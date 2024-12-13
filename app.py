from flask import Flask, jsonify
from temp_gmail import GMail
import time
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# 使用简单的内存缓存(生产环境建议使用Redis)
class EmailCache:
    def __init__(self):
        self.cache = {}
        
    def add(self, email, gmail):
        # 设置1小时过期
        self.cache[email] = {
            'instance': gmail,
            'expires': datetime.now() + timedelta(hours=1)
        }
        
    def get(self, email):
        if email in self.cache:
            data = self.cache[email]
            if datetime.now() < data['expires']:
                return data['instance']
            else:
                del self.cache[email]
        return None
        
    def cleanup(self):
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if now >= v['expires']]
        for k in expired:
            del self.cache[k]

email_cache = EmailCache()

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Temp Gmail Service is running'
    })

@app.route('/create_email', methods=['GET'])
def create_email():
    try:
        # 清理过期的邮箱实例
        email_cache.cleanup()
        
        # 创建新的Gmail实例
        gmail = GMail()
        email = gmail.create_email()
        
        # 保存实例到缓存
        email_cache.add(email, gmail)
        
        return jsonify({
            'success': True,
            'email': email
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/check_email/<path:email>', methods=['GET'])
def check_email(email):
    try:
        # 从缓存获取Gmail实例
        gmail = email_cache.get(email)
        if not gmail:
            return jsonify({
                'success': False,
                'error': 'Email not found or expired'
            }), 404
            
        emails = gmail.load_list()
        
        # 如果有新邮件,获取最新一封的内容
        if 'messageData' in emails and emails['messageData']:
            latest_email = emails['messageData'][0]
            message_content = gmail.load_item(latest_email['messageID'])
            
            return jsonify({
                'success': True,
                'has_new': True,
                'message': message_content,
                'subject': latest_email.get('subject', ''),
                'from': latest_email.get('from', ''),
                'time': latest_email.get('time', '')
            })
        
        return jsonify({
            'success': True,
            'has_new': False
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 添加健康检查接口
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'cache_size': len(email_cache.cache)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000) 