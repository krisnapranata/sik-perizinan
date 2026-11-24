# Dipakai bersama oleh setiap location yang meneruskan ke Django (lihat nginx.conf).
proxy_pass $sik_web;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $proto_asli;
proxy_read_timeout 120s;
proxy_send_timeout 120s;
# Header keamanan dipasang Nginx di atas; cegah nilai ganda yang saling bertentangan.
proxy_hide_header X-Frame-Options;
proxy_hide_header X-Content-Type-Options;
