#
# Setup RabbitMQ
#
cd $PHYLOBOT_REPO
sudo bash aws_setup/install_rabbitmq.sh
sudo rabbitmqctl add_user myuser mypassword
sudo rabbitmqctl set_user_tags myuser mytag
sudo rabbitmqctl set_permissions -p myvhost myuser ".*" ".*" ".*"
sudo rabbitmq-server -detached