-- HMS password reset init file
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'hms@2024';
FLUSH PRIVILEGES;
