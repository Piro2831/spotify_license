import os
import random
import string
import psycopg2
import threading
import time
import requests
from flask import Flask, render_template_string, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_for_session')
def keep_alive():
    # 自分のURLをここに記述してください
    URL = "https://spotify-license.onrender.com/" 
    while True:
        try:
            requests.get(URL)
            print("Self-ping sent.")
        except Exception as e:
            print(f"Ping failed: {e}")
        # 10分（600秒）おきにアクセス
        time.sleep(400)

# スレッドを開始
thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    # sslmode=require は必須です
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    if not DATABASE_URL:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            used BOOLEAN NOT NULL DEFAULT FALSE
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

def generate_random_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

@app.route('/reset/<license_key>', methods=['POST'])
def reset_license(license_key):
    if session.get('is_admin'):
        conn = get_db_connection()
        cur = conn.cursor()
        # used を明示的に FALSE に更新
        cur.execute('UPDATE licenses SET used = FALSE WHERE key = %s', (license_key,))
        conn.commit()
        cur.close()
        conn.close()
        flash(f'ライセンス {license_key} を未使用に戻しました。', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/', methods=['GET', 'POST'])
def claim_account():
    account_data = None
    error_msg = None
    
    if request.method == 'POST':
        entered_key = request.form.get('license_key', '').strip()
        
        if entered_key == "owner_Piropiroro9999hits":
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
            
        if not entered_key:
            error_msg = 'ライセンスキーを入力してください。'
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            # データベースから最新の情報を取得
            cur.execute('SELECT email, password, used FROM licenses WHERE key = %s', (entered_key,))
            row = cur.fetchone()
            
            if not row:
                error_msg = '無効なライセンスキーです。'
            elif row[2] == True: # 明示的に True と比較
                error_msg = 'このライセンスキーはすでに使用されています。'
            else:
                # 使用済みに更新
                cur.execute('UPDATE licenses SET used = TRUE WHERE key = %s', (entered_key,))
                conn.commit()
                account_data = {'email': row[0], 'password': row[1]}
            
            cur.close()
            conn.close()
            
    return render_template_string(CLIENT_HTML, account=account_data, error=error_msg)

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('claim_account'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT key, email, password, used FROM licenses ORDER BY key ASC')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    licenses_dict = {}
    for row in rows:
        licenses_dict[row[0]] = {'email': row[1], 'password': row[2], 'used': row[3]}
        
    return render_template_string(ADMIN_HTML, licenses=licenses_dict)

@app.route('/add', methods=['POST'])
def add_license():
    if not session.get('is_admin'): 
        return "Unauthorized", 403
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    if email and password:
        new_key = generate_random_key()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO licenses (key, email, password, used) VALUES (%s, %s, %s, FALSE)', (new_key, email, password))
        conn.commit()
        cur.close()
        conn.close()
        flash(f'新しいライセンスを発行しました: {new_key}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete/<license_key>', methods=['POST'])
def delete_license(license_key):
    if session.get('is_admin'):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM licenses WHERE key = %s', (license_key,))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('claim_account'))

# ... (CLIENT_HTML と ADMIN_HTML はそのまま変更不要です)

CLIENT_HTML = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotifyアカウント受取ページ</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: sans-serif; background: #121212; color: #fff; margin: 0; padding: 15px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { width: 100%; max-width: 450px; background: #1e1e1e; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; }
        h1 { color: #1db954; font-size: 1.5rem; margin-bottom: 20px; }
        form { display: flex; flex-direction: column; gap: 15px; }
        input { width: 100%; padding: 12px; background: #2a2a2a; border: 1px solid #444; color: #fff; border-radius: 6px; font-size: 1rem; text-align: center; }
        button { width: 100%; padding: 12px; background: #1db954; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 1rem; }
        button:hover { background: #1aa34a; }
        .error { background: rgba(255, 0, 0, 0.2); border: 1px solid #ff4444; color: #ff4444; padding: 10px; border-radius: 6px; margin-bottom: 15px; font-size: 0.9rem; }
        .result-box { background: #2a2a2a; border: 1px solid #1db954; padding: 15px; border-radius: 6px; margin-top: 20px; text-align: left; }
        .result-box p { margin: 10px 0; word-break: break-all; font-size: 0.95rem; }
        .label { color: #aaa; font-size: 0.8rem; display: block; margin-bottom: 3px; }
        .row-flex { display: flex; gap: 8px; align-items: center; }
        .row-flex input { flex: 1; text-align: left; padding: 8px 10px; font-size: 0.9rem; }
        .copy-btn { padding: 8px 12px; background: #333; border: 1px solid #555; color: #fff; border-radius: 4px; cursor: pointer; font-size: 0.85rem; width: auto; white-space: nowrap; }
        .copy-btn:hover { background: #444; }
        .discord-section { margin-top: 30px; border-top: 1px solid #333; padding-top: 20px; font-size: 0.9rem; color: #ccc; }
        .discord-link { display: inline-flex; align-items: center; justify-content: center; gap: 8px; margin-top: 10px; text-decoration: none; color: #fff; background: #5865F2; padding: 10px 15px; border-radius: 6px; font-weight: bold; width: 100%; }
        .discord-link:hover { background: #4752C4; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Spotifyアカウント受取</h1>
        
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}

        {% if account %}
            <div class="result-box">
                <p><strong>認証成功！アカウント情報はこちらです：</strong></p>
                <div style="margin-bottom: 12px;">
                    <span class="label">メールアドレス:</span>
                    <div class="row-flex">
                        <input type="text" id="email-val" value="{{ account.email }}" readonly>
                        <button class="copy-btn" onclick="copyText('email-val', this)">コピー</button>
                    </div>
                </div>
                <div>
                    <span class="label">パスワード:</span>
                    <div class="row-flex">
                        <input type="text" id="pass-val" value="{{ account.password }}" readonly>
                        <button class="copy-btn" onclick="copyText('pass-val', this)">コピー</button>
                    </div>
                </div>
            </div>
            <p style="margin-top: 15px; font-size: 0.85rem; color: #888;">※この情報は再度表示されないため、必ず保存してください。</p>
        {% else %}
            <form action="/" method="POST">
                <input type="text" name="license_key" placeholder="ライセンスキーを入力" required autocomplete="off">
                <button type="submit">アカウントを発行する</button>
            </form>
        {% endif %}

        <div class="discord-section">
            <p>ディスコードサーバーはこちら↓</p>
            <a href="https://discord.gg/k6uqzf3AYe" target="_blank" class="discord-link">
                <svg width="22" height="17" fill="currentColor" viewBox="0 0 127.14 96.36"><path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1,105.25,105.25,0,0,0,32.19-16.15c2.65-27.28-4.41-51.12-19.13-72.15ZM42.45,65.69C36.18,65.69,31,60,31,53s5.18-12.72,11.45-12.72S53.9,46,53.88,53,48.72,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5.18-12.72,11.44-12.72S96.15,46,96.13,53,91,65.69,84.69,65.69Z"/></svg>
                <span>Discordサーバーに参加</span>
            </a>
        </div>
    </div>

    <script>
    function copyText(elementId, btn) {
        const copyText = document.getElementById(elementId);
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        navigator.clipboard.writeText(copyText.value).then(() => {
            const originalText = btn.innerText;
            btn.innerText = 'コピー完了!';
            btn.style.background = '#1db954';
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.background = '#333';
            }, 1500);
        });
    }
    </script>
</body>
</html>
'''

ADMIN_HTML = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ライセンス管理パネル</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: sans-serif; background: #121212; color: #fff; margin: 0; padding: 15px; }
        .container { max-width: 800px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h1, h2 { color: #1db954; font-size: 1.3rem; }
        form { display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px; }
        input { padding: 12px; background: #2a2a2a; border: 1px solid #444; color: #fff; border-radius: 6px; font-size: 1rem; width: 100%; }
        button { padding: 12px; background: #1db954; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 1rem; }
        button:hover { background: #1aa34a; }
        .alert { padding: 10px; margin-bottom: 15px; border-radius: 6px; font-size: 0.9rem; }
        .alert.success { background: rgba(29, 185, 84, 0.2); border: 1px solid #1db954; }
        .table-responsive { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; min-width: 600px; font-size: 0.9rem; }
        th, td { padding: 10px; border-bottom: 1px solid #333; text-align: left; }
        th { background: #2a2a2a; }
        .badge-used { color: #ff4444; font-weight: bold; }
        .badge-unused { color: #1db954; font-weight: bold; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .back-link { color: #aaa; text-decoration: none; font-size: 0.9rem; background: #2a2a2a; padding: 8px 12px; border-radius: 6px; }
        .back-link:hover { color: #fff; background: #333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="top-bar">
            <h1>管理パネル</h1>
            <a href="/logout" class="back-link">利用者画面へ戻る</a>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <h2>アカウント登録（自動でライセンス発行）</h2>
        <form action="/add" method="POST">
            <input type="email" name="email" placeholder="Spotify用 メールアドレス" required autocomplete="off">
            <input type="text" name="password" placeholder="Spotify用 パスワード" required autocomplete="off">
            <button type="submit">ランダムなライセンスを発行して登録する</button>
        </form>

        <h2>登録済みライセンス一覧</h2>
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>ライセンスキー</th>
                        <th>メールアドレス</th>
                        <th>パスワード</th>
                        <th>状態</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for key, data in licenses.items() %}
                    <tr>
                        <td><code>{{ key }}</code></td>
                        <td>{{ data.email }}</td>
                        <td><code>{{ data.password }}</code></td>
<td>
                            {% if data.used %}
                                <span class="badge-used">使用済み</span>
                            {% else %}
                                <span class="badge-unused">未使用</span>
                            {% endif %}
                        </td>
                        <td>
                            <div style="display: flex; gap: 5px;">
                                {% if data.used %}
                                <form action="/reset/{{ key }}" method="POST" style="margin:0;">
                                    <button type="submit" style="background: #1db954; padding: 6px 8px; font-size: 0.8rem;">再使用可</button>
                                </form>
                                {% endif %}
                                <form action="/delete/{{ key }}" method="POST" style="margin:0;">
                                    <button type="submit" style="background: #ff4444; padding: 6px 8px; font-size: 0.8rem;">削除</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="text-align: center; color: #888;">登録されているライセンスはありません。</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
