proxy_pass http://127.0.0.1:8000;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto https;
proxy_read_timeout 120s;
# Header keamanan dipasang Nginx di atas; cegah nilai ganda yang saling bertentangan.
proxy_hide_header X-Frame-Options;
proxy_hide_header X-Content-Type-Options;
