cd ..
git clone https://github.com/jcjohnson/neural-style.git neural-style
sh neural-style/models/download_models.sh
cp neural-style/models NeuralStyleServer/models -R
sudo apt-get install nginx
sudo /etc/init.d/nginx start
sudo rm /etc/nginx/sites-enabled/default 
sudo touch /etc/nginx/sites-available/flask_settings
sudo ln -s /etc/nginx/sites-available/flask_settings /etc/nginx/sites-enabled/flask_settings
sudo echo -e "server {\n        location / {\n                proxy_pass http://127.0.0.1:8000;\n                proxy_set_header Host \$host;\n                proxy_set_header X-Real-IP \$remote_addr;\n        }\n}\n" >> /etc/nginx/sites-enabled/flask_settings
sudo /etc/init.d/nginx restart
sudo apt-get install gunicorn
sudo /etc/init.d/nginx restart