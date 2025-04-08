#!/bin/bash

LB_DNS=$1

# Update system packages
yum update -y

# Install Node.js
curl -sL https://rpm.nodesource.com/setup_20.x | bash -
yum install -y nodejs

# Install Git
yum install -y git

# Install Nginx
amazon-linux-extras install nginx1 -y

# Start Nginx service
systemctl start nginx
systemctl enable nginx

# Clone repository
cd /opt
git clone https://github.com/msshashank1997/travel-memory.git
cd travel-memory

# Setup backend
cd travel-memory/backend
cp .env.example .env
# Update .env file with necessary configurations
cat > .env << EOF
MONGO_URI='mongodb+srv://username:password@cluster0.gdzal.mongodb.net/dbname'
PORT=3001
EOF

# Install dependencies and start the backend
npm install
npm install pm2 -g
pm2 start index.js --name "travel-memory-backend"

# Setup frontend
cd ../frontend
# Update URL configuration
cat > src/utils/urls.js << EOF
const BACKEND_URL = 'http://${LB_DNS}/api';
export default BACKEND_URL;
EOF

# Install dependencies and build the frontend
npm install
npm run build

# Configure Nginx to serve the frontend and proxy backend requests
cat > /etc/nginx/conf.d/travel-memory.conf << EOF
server {
    listen 80;
    server_name _;

    location / {
        root /opt/travel-memory/frontend/build;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Remove default nginx configuration
rm -f /etc/nginx/conf.d/default.conf

# Restart Nginx to apply changes
systemctl restart nginx

# Start the frontend with PM2
cd /opt/travel-memory/frontend
pm2 serve build 3001 --name "travel-memory-frontend" --spa

# Ensure PM2 starts on boot
pm2 startup
pm2 save

echo "TravelMemory application setup completed!"
