import boto3
import os
from botocore.exceptions import ClientError

def create_vpc(ec2_client, cidr_block='172.31.0.0/16'):
    try:
        # Create VPC
        response = ec2_client.create_vpc(CidrBlock=cidr_block)
        vpc_id = response['Vpc']['VpcId']
        print(f"VPC created with ID: {vpc_id}")
        
        # Enable DNS support and DNS hostnames
        ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
        ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
        
        # Create a name tag for the VPC
        ec2_client.create_tags(
            Resources=[vpc_id],
            Tags=[{'Key': 'Name', 'Value': 'FullStackApp-VPC'}]
        )
        return vpc_id
    except Exception as e:
        print(f"Error creating VPC: {e}")
        return None

def create_security_group(ec2_client, vpc_id, name, description):
    try:
        response = ec2_client.create_security_group(
            GroupName=name,
            Description=description,
            VpcId=vpc_id
        )
        security_group_id = response['GroupId']
        print(f"Security Group {name} created with ID: {security_group_id}")
        
        # Add inbound rules
        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                # HTTP
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # HTTPS
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # SSH
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        print(f"Inbound rules added to Security Group {name}")
        return security_group_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
            print(f"Security Group {name} already exists")
            # Get the group ID of the existing security group
            response = ec2_client.describe_security_groups(
                Filters=[
                    {
                        'Name': 'group-name',
                        'Values': [name]
                    },
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            )
            security_group_id = response['SecurityGroups'][0]['GroupId']
            return security_group_id
        else:
            print(f"Error creating Security Group: {e}")
            return None

def create_instances(ec2_resource, security_group_id, key_name, count=2, instance_type='t2.micro'):
    try:
        # Ubuntu 20.04 LTS AMI (replace with the appropriate AMI ID for your region)
        ami_id = 'ami-0e35ddab05955cf57'  # Ubuntu 20.04 LTS in ap-south-1
        
        # User data script to install necessary software
        user_data = r'''#!/bin/bash

    # Update & install system dependencies
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y nginx git curl build-essential

    # Install Node.js (LTS) and npm
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
    sudo apt-get install -y nodejs
    sudo apt-get install -y npm
    sudo npm install -g npm@11.3.0

    # Install PM2 globally
    sudo npm install -g pm2

    # Clone the TravelMemory repo
    cd /home/ubuntu
    git clone https://github.com/username/TravelMemory.git
    cd TravelMemory

    # ------------------------
    # Setup Backend
    # ------------------------
    cd backend
    sudo npm install

    # Create .env file for backend
    sudo bash -c cat <<EOF > .env
PORT=3001
MONGO_URI='replace_with_your_mongo_uri'
EOF

    # Start backend using PM2
    sudo pm2 start index.js --name travel-backend -f
    sudo pm2 save
    sudo pm2 startup --silent

    # ------------------------
    # Setup Frontend
    # ------------------------
    cd ../frontend
    sudo npm install

    # Build frontend with base API path as /api
    sudo REACT_APP_API_URL=/api npm run build

    # Serve frontend via NGINX
    sudo cp -r build/* /var/www/html/

    # ------------------------
    # Configure NGINX
    # ------------------------
    sudo bash -c 'cat > /etc/nginx/sites-available/default' << 'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    location /api {
        proxy_pass http://localhost:3001/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

    # Restart NGINX to apply changes
    sudo systemctl restart nginx
    '''
        
        instances = ec2_resource.create_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            MinCount=count,
            MaxCount=count,
            KeyName=key_name,
            SecurityGroupIds=[security_group_id],
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'shashank'
                        },
                        {
                            'Key': 'batch',
                            'Value': 'batch10'
                        }
                    ]
                }
            ]
        )
        
        print(f"Created {len(instances)} instances")
        
        # Wait for instances to be running
        for instance in instances:
            instance.wait_until_running()
            instance.reload()
            print(f"Instance {instance.id} is running at {instance.public_dns_name}")
        
        return instances
    except Exception as e:
        print(f"Error creating instances: {e}")
        return []

def create_load_balancer(client, name, subnets, security_group_id, instances):
    try:
        # Create target group
        response = client.create_target_group(
            Name=f"{name}-target",
            Protocol='HTTP',
            Port=80,
            VpcId=instances[0].vpc_id,
            HealthCheckProtocol='HTTP',
            HealthCheckPath='/api',  # Updated health check path
            TargetType='instance'
        )
        target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
        
        # Register instances with target group
        instance_ids = [instance.id for instance in instances]
        client.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{'Id': id} for id in instance_ids]
        )
        
        # Create load balancer
        response = client.create_load_balancer(
            Name=name,
            Subnets=subnets,
            SecurityGroups=[security_group_id],
            Scheme='internet-facing',
            Type='application'
        )
        lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']
        lb_dns = response['LoadBalancers'][0]['DNSName']
        
        # Create listener
        client.create_listener(
            LoadBalancerArn=lb_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': target_group_arn
                }
            ]
        )
        
        print(f"Load balancer created with DNS name: {lb_dns}")
        return lb_dns
    except Exception as e:
        print(f"Error creating load balancer: {e}")
        return None

def main():
    # Initialize boto3 clients and resources
    ec2_client = boto3.client('ec2', region_name='ap-south-1')
    ec2_resource = boto3.resource('ec2', region_name='ap-south-1')
    elbv2_client = boto3.client('elbv2', region_name='ap-south-1')
    
    # Create VPC
    vpc_id = create_vpc(ec2_client)
    if not vpc_id:
        print("Failed to create VPC. Exiting.")
        return
    
    # Get subnet IDs from different Availability Zones
    response = ec2_client.describe_subnets(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )

    # Group subnets by Availability Zone
    subnets_by_az = {}
    for subnet in response['Subnets']:
        az = subnet['AvailabilityZone']
        subnet_id = subnet['SubnetId']
        if az not in subnets_by_az:
            subnets_by_az[az] = []
        subnets_by_az[az].append(subnet_id)

    # Select one subnet from each Availability Zone
    subnet_ids = []
    for az, subnet_list in subnets_by_az.items():
        if subnet_list:
            subnet_ids.append(subnet_list[0])
        if len(subnet_ids) >= 2:  # We need at least 2 subnets
            break

    # Check if we have enough subnets from different AZs
    if len(subnet_ids) < 2:
        print("Error: Need at least 2 subnets in different Availability Zones")
        return
    
    # Create or get existing security group
    security_group_id = create_security_group(
        ec2_client, 
        vpc_id, 
        'FullStackApp-1-SG', 
        'Security group for full-stack application'
    )
    
    if not security_group_id:
        print("Failed to create or get security group. Exiting.")
        return
    
    # Create key pair if it doesn't exist
    key_name = 'fullstack-app-key'
    try:
        ec2_client.describe_key_pairs(KeyNames=[key_name])
        print(f"Key pair {key_name} already exists")
    except ec2_client.exceptions.ClientError:
        print(f"Creating new key pair: {key_name}")
        response = ec2_client.create_key_pair(KeyName=key_name)
        private_key = response['KeyMaterial']
        
        # Save private key to file
        with open(f"{key_name}.pem", 'w') as f:
            f.write(private_key)
        os.chmod(f"{key_name}.pem", 0o400)
        print(f"Private key saved to {key_name}.pem")
    
    # Create EC2 instances
    instances = create_instances(ec2_resource, security_group_id, key_name, count=2)
    
    if not instances:
        print("Failed to create instances. Exiting.")
        return
    
    # Create load balancer
    lb_dns = create_load_balancer(elbv2_client, 'fullstack-app-lb', subnet_ids, security_group_id, instances)
    
    if not lb_dns:
        print("Failed to create load balancer. Exiting.")
        return
    
    print("\nDeployment completed successfully!")
    print(f"Application is accessible at: http://{lb_dns}")
    print("To access your EC2 instances:")
    for i, instance in enumerate(instances):
        print(f"Instance {i+1}: ssh -i {key_name}.pem ubuntu@{instance.public_dns_name}")
    
    print("\nNext steps:")
    print("1. Set up Cloudflare to point your custom domain to the load balancer DNS")
    print("2. Configure HTTPS on the load balancer")
    print("3. SSH into your instances to verify the application is running correctly")

if __name__ == "__main__":
    main()
