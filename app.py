import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_for_session')

# 簡易DB
licenses_db = {}

def generate_random_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

# 利用者向けページをルートに設定
@app.route('/', methods=['GET', 'POST'])
def claim_account():
    account_data = None
    error_msg = None
    
    if request.method == 'POST':
        entered_key = request.form.get('license_key', '').strip()
        
        # 隠しコマンド：管理者ログイン
        if entered_key == "owner_piro9999hits":
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
            
        if not entered_key:
            error_msg = 'ライセンスキーを入力してください。'
        elif entered_key not in licenses_db:
            error_msg = '無効なライセンスキーです。'
        elif licenses_db[entered_key]['used']:
            error_msg = 'このライセンスキーはすでに使用されています。'
        else:
            licenses_db[entered_key]['used'] = True
            account_data = licenses_db[entered_key]
            
    return render_template('client.html', account=account_data, error=error_msg)

# 管理者専用ページ
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('claim_account'))
    return render_template('index.html', licenses=licenses_db)

@app.route('/add', methods=['POST'])
def add_license():
    if not session.get('is_admin'): return "Unauthorized", 403
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    if email and password:
        new_key = generate_random_key()
        licenses_db[new_key] = {'email': email, 'password': password, 'used': False}
        flash(f'新しいライセンスを発行しました: {new_key}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete/<license_key>', methods=['POST'])
def delete_license(license_key):
    if session.get('is_admin') and license_key in licenses_db:
        del licenses_db[license_key]
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
