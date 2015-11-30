#
# Install Nginx
# (In Ubuntu, nginx will auto start upon installation)
#
sudo apt-get -y install nginx
sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.old
sudo cp aws_setup/nginx.conf /etc/nginx/nginx.conf

#
# Launch Nginx with the new configuration.
# Because nginx is launched upon installation (in previous steps), 
# we need to restart nginx to ensure that correct configurations
# are loaded.
#
sudo /etc/init.d/nginx stop
sudo /etc/init.d/nginx reload
sudo /etc/init.d/nginx start