#
# Install PostgreSQL
#
sudo apt-get -y install postgresql postgresql-contrib libpq-dev
sudo -u postgres psql -c "CREATE DATABASE phylobotdb"
sudo -u postgres psql --dbname=phylobotdb -c "CREATE USER django WITH PASSWORD 'phylobotpass'"
sudo -u postgres psql --dbname=phylobotdb -c "ALTER ROLE django SET timezone TO 'UTC-8'"
sudo -u postgres psql --dbname=phylobotdb -c "ALTER USER django CREATEDB"
sudo -u postgres psql --dbname=phylobotdb -c "GRANT ALL PRIVILEGES ON DATABASE phylobotdb TO django"
#sudo -u postgres psql --dbname=phylobotdb -c "ALTER USER CREATEDB"