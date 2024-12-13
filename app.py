const EMAIL_SERVICE_API = 'https://email-orpin.vercel.app';
const EMAIL_CHECK_INTERVAL = 5000; // 5秒检查一次
const MAX_EMAIL_CHECK_ATTEMPTS = 12; // 最多检查1分钟

function encodeEmailForUrl(email) {
  const [localPart, domain] = email.split('@');
  return `${encodeURIComponent(localPart)}@${encodeURIComponent(domain)}`;
}

async function getVerificationCode(username, domain) {
  try {
    console.log('[Email] 开始创建临时邮箱');
    // 创建临时邮箱
    const createResponse = await fetch(`${EMAIL_SERVICE_API}/create_email`);
    const createData = await createResponse.json();
    
    if (!createData.success) {
      console.error('[Email] 创建邮箱失败:', createData.error);
      throw new Error('Failed to create email');
    }
    
    const email = createData.email;
    console.log(`[Email] 成功创建临时邮箱: ${email}`);
    
    // 循环检查新邮件
    console.log('[Email] 开始等待验证邮件');
    for (let attempt = 0; attempt < MAX_EMAIL_CHECK_ATTEMPTS; attempt++) {
      console.log(`[Email] 第${attempt + 1}次检查邮件`);
      
      // 使用新的编码函数处理邮箱地址
      const encodedEmail = encodeEmailForUrl(email);
      const checkResponse = await fetch(`${EMAIL_SERVICE_API}/check_email/${encodedEmail}`);
      const checkData = await checkResponse.json();
      
      if (checkData.success && checkData.has_new) {
        console.log('[Email] 收到新邮件:', {
          from: checkData.from,
          subject: checkData.subject,
          time: checkData.time
        });
        
        // 从邮件内容中提取验证码
        const codeMatch = checkData.message.match(/<strong>([a-z0-9]+)<\/strong>/i);
        if (codeMatch) {
          const code = codeMatch[1];
          console.log(`[Email] 成功提取验证码: ${code}`);
          return code;
        }
      }
      
      // 等待下次检查
      await new Promise(resolve => setTimeout(resolve, EMAIL_CHECK_INTERVAL));
    }
    
    console.error('[Email] 超时未收到验证码');
    throw new Error('未能获取验证码');
  } catch (error) {
    console.error('[Email] 获取验证码失败:', error);
    throw error;
  }
}

// 添加健康检查函数
async function checkEmailServiceHealth() {
  try {
    const response = await fetch(`${EMAIL_SERVICE_API}/health`);
    const data = await response.json();
    return data.status === 'healthy';
  } catch (error) {
    console.error('[Health] 邮件服务健康检查失败:', error);
    return false;
  }
}
