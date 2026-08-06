import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here_for_development')

# ライセンスとアカウントを保存する辞書（※本番運用時はデータベース推奨ですが、まずはこれで動作します）
# 構造: { "LICENSE_KEY": { "email": "...", "password": "...", "used": False } }
licenses_db = {}

# 管理者画面（ライセンス・アカウントの登録・一覧）
@app.route('/')
def admin_dashboard():
    return render_template('index.html', licenses=licenses_db)

# ライセンス＆アカウントの追加処理
@app.route('/add', methods=['POST'])
def add_license():
    license_key = request.form.get('license_key')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not license_key or not email or not password:
        flash('すべてのフィールドを入力してください。', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if license_key in licenses_db:
        flash('そのライセンスキーはすでに存在します。', 'error')
        return redirect(url_for('admin_dashboard'))
        
    licenses_db[license_key] = {
        'email': email,
        'password': password,
        'used': False
    }
    flash('ライセンスとアカウント情報を追加しました。', 'success')
    return redirect(url_for('admin_dashboard'))

# 登録済みライセンスの削除処理
@app.route('/delete/<license_key>', methods=['POST'])
def delete_license(license_key):
    if license_key in licenses_db:
        del licenses_db[license_key]
        flash('ライセンスを削除しました。', 'success')
    return redirect(url_for('admin_dashboard'))

# 利用者向け受取ページ
@app.route('/claim', methods=['GET', 'POST'])
def claim_account():
    account_data = None
    error_msg = None
    
    if request.method == 'POST':
        entered_key = request.form.get('license_key', '').strip()
        
        if not entered_key:
            error_msg = 'ライセンスキーを入力してください。'
        elif entered_key not in licenses_db:
            error_msg = '無効なライセンスキーです。'
        elif licenses_db[entered_key]['used']:
            error_msg = 'このライセンスキーはすでに使用されています。'
        else:
            # 一度使われたら使用済みに変更してアカウント情報を返す
            licenses_db[entered_key]['used'] = True
            account_data = licenses_db[entered_key]
            
    return render_template('client.html', account=account_data, error=error_msg)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
