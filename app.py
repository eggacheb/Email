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
        
    def normalize_email(self, email):
        """规范化邮箱地址，保持点分隔的格式"""
        # 移除空白字符但保留点
        email = email.lower().strip()
        # 确保@前的点保持不变
        local_part, domain = email.split('@')
        return f"{local_part}@{domain}"
        
    def add(self, email, gmail):
        email = self.normalize_email(email)
        self.cache[email] = {
            'instance': gmail,
            'expires': datetime.now() + timedelta(hours=1)
        }
        print(f"[Cache] 添加邮箱实例: {email}")
        
    def get(self, email):
        email = self.normalize_email(email)
        if email in self.cache:
            data = self.cache[email]
            if datetime.now() < data['expires']:
                print(f"[Cache] 找到邮箱实例: {email}")
                return data['instance']
            else:
                print(f"[Cache] 邮箱实例已过期: {email}")
                del self.cache[email]
        else:
            print(f"[Cache] 未找到邮箱实例: {email}")
        return None
        
    def cleanup(self):
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if now >= v['expires']]
        for k in expired:
            print(f"[Cache] 清理过期实例: {k}")
            del self.cache[k]

email_cache = EmailCache()

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Temp Gmail Service is running',
        'cache_size': len(email_cache.cache)
    })

@app.route('/create_email', methods=['GET'])
def create_email():
    try:
        # 清理过期的邮箱实例
        email_cache.cleanup()
        
        # 最多尝试5次创建邮箱
        for attempt in range(5):
            # 创建新的Gmail实例
            gmail = GMail()
            email = gmail.create_email()
            print(f"[API] 尝试创建邮箱 (第{attempt + 1}次): {email}")
            
            # 检查邮箱格式，不要带"+"的邮箱
            if '+' not in email:
                print(f"[API] 成功创建合适的邮箱: {email}")
                # 保存实例到缓存
                email_cache.add(email, gmail)
                return jsonify({
                    'success': True,
                    'email': email
                })
            else:
                print(f"[API] 跳过不合适的邮箱格式: {email}")
                continue
        
        # 如果多次尝试都失败
        raise Exception("无法创建合适格式的邮箱")
        
    except Exception as e:
        print(f"[Error] 创建邮箱失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/check_email/<path:email>', methods=['GET'])
def check_email(email):
    try:
        print(f"[API] 检查邮箱: {email}")
        gmail = email_cache.get(email)
        if not gmail:
            print(f"[API] 邮箱不存在或已过期: {email}")
            return jsonify({
                'success': False,
                'error': 'Email not found or expired'
            }), 404
            
        print(f"[API] 加载邮件列表: {email}")
        emails = gmail.load_list()
        print(f"[API] 邮件列表: {emails}")
        
        if 'messageData' in emails and emails['messageData']:
            # 过滤掉AI TOOLS的邮件
            valid_emails = [
                e for e in emails['messageData'] 
                if e['from'] != 'AI TOOLS'
            ]
            
            if valid_emails:
                # 获取最新的非AI TOOLS邮件
                latest_email = valid_emails[0]
                print(f"[API] 发现新邮件: {latest_email}")
                
                try:
                    message_content = gmail.load_item(latest_email['messageID'])
                    print(f"[API] 邮件内容: {message_content}")
                except Exception as e:
                    print(f"[API] 获取邮件内容失败: {str(e)}")
                    message_content = "Failed to load message content"
                
                response_data = {
                    'success': True,
                    'has_new': True,
                    'message': message_content,
                    'subject': latest_email.get('subject', ''),
                    'from': latest_email.get('from', ''),
                    'time': latest_email.get('time', ''),
                    'raw_email': latest_email
                }
                print(f"[API] 返回数据: {response_data}")
                return jsonify(response_data)
            else:
                print(f"[API] 没有找到有效的新邮件")
        
        return jsonify({
            'success': True,
            'has_new': False
        })
        
    except Exception as e:
        print(f"[Error] 检查邮件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 添加健康检查接口
@app.route('/health')
def health_check():
    cache_info = {
        'size': len(email_cache.cache),
        'emails': list(email_cache.cache.keys())
    }
    print(f"[Health] 缓存状态: {cache_info}")
    return jsonify({
        'status': 'healthy',
        'cache': cache_info
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000) 
