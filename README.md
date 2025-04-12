# Full-Stack Application Deployment with AWS and Boto3

This project automates the deployment of a full-stack application (Node.js backend + React frontend) on AWS EC2 instances with load balancing and Cloudflare integration.

## Prerequisites

- AWS account with appropriate permissions
- Python 3.6+ installed
- Boto3 installed (`pip install boto3`)
- AWS credentials configured (`aws configure`)
- Cloudflare account (for custom domain)

## Setup Instructions

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/yourrepo.git
   cd yourrepo
   ```


2. Install required Python packages:
   
   ```
   pip install boto3
   pip insatll os
   ```

3. In the `infra-deployment.py` replace you repo name with

4. Run the deployment script:
   
   ```
   python infra-deployment.py
   ```

5. The script will:
   - Create a VPC with necessary network settings
   - Create a security group with HTTP, HTTPS, and SSH access
   - Create a key pair for SSH access
   - Launch EC2 instances with the TravelMemory application
   - Set up a load balancer across multiple availability zones
   - Install and configure the Node.js backend and React frontend on each instance
   - Configure Nginx as a reverse proxy

     ![deployment-script-output](https://github.com/user-attachments/assets/9c2ca5ab-e06f-4a8d-a94a-175e29074fe8)

## Cloudflare Configuration

After your AWS infrastructure is set up, you can configure Cloudflare to point your domain to the load balancer:

1. **DNS Configuration**:
   - Log in to your Cloudflare account
   - Select your domain and go to the DNS section
   - Add a CNAME record:
     - Name: Your subdomain (e.g., `app` for app.yourdomain.com) or `@` for root domain
     - Target: Your AWS load balancer DNS (e.g., `fullstack-app-lb-123456789.ap-south-1.elb.amazonaws.com`)
     - Proxy status: Proxied (for Cloudflare benefits)

2. **SSL/TLS Configuration**:
   - Go to the SSL/TLS section in Cloudflare
   - Set SSL/TLS encryption mode to "Full" or "Full (strict)"
   - Enable "Always Use HTTPS" to redirect HTTP to HTTPS

## Application Architecture

- **Frontend**: React application served from Nginx
- **Backend**: Node.js application running on port 3001
- **Nginx**: Acts as a reverse proxy, routing API requests to the backend
- **Load Balancer**: Distributes traffic across multiple EC2 instances
- **Cloudflare**: Provides DNS management, CDN, and security
  - **DNS Management**: Routes domain name to load balancer
  - **CDN**: Caches static content at edge locations
  - **Security**: Provides DDoS protection, WAF, and SSL

      ![Untitled Diagram drawio](https://github.com/user-attachments/assets/c900bec1-ed38-479b-88ba-92f5e0f473db)

## Maintenance

- SSH into instances: `ssh -i fullstack-app-key.pem ubuntu@instance-public-dns`
- Check application logs: `pm2 logs`
- Restart the backend: `pm2 restart travel-backend`
- Update the application: Update your code repository and run deployment again

## Scaling

The deployment creates multiple instances by default. To adjust the number of instances:

1. Modify the `count` parameter in the `create_instances` function call in `deploy.py`
2. Run the deployment script again

## Troubleshooting

- If instances fail to start, check the AWS Console for error messages
- For application issues, check the logs using `pm2 logs` on the instances
- For load balancer issues, check the health check settings in the AWS Console
- For Cloudflare issues:
  - Check DNS propagation with `dig yourdomain.com +trace`
  - Verify Cloudflare is properly proxying with orange cloud icon
  - Check SSL/TLS settings if encountering certificate errors
