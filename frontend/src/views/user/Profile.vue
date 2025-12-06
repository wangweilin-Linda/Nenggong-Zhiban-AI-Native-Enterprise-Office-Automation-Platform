<template>
  <div class="user-profile">
    <div class="profile-header">
      <h1>个人资料设置</h1>
    </div>
    
    <div class="profile-content">
      <!-- 个人信息部分 -->
      <div class="section personal-info">
        <h2>个人信息</h2>
        <form @submit.prevent="updateProfile">
          <div class="form-group">
            <label for="username">用户名</label>
            <input type="text" id="username" v-model="userInfo.username" disabled />
            <small>用户名不可修改</small>
          </div>
          
          <div class="form-group">
            <label for="fullName">姓名</label>
            <input type="text" id="fullName" v-model="userInfo.fullName" />
          </div>
          
          <div class="form-group">
            <label for="email">邮箱</label>
            <input type="email" id="email" v-model="userInfo.email" />
          </div>
          
          <div class="form-group">
            <label for="department">部门</label>
            <input type="text" id="department" v-model="userInfo.department" disabled />
            <small>部门信息由管理员设置</small>
          </div>
          
          <div class="form-group">
            <label for="position">职位</label>
            <input type="text" id="position" v-model="userInfo.position" disabled />
            <small>职位信息由管理员设置</small>
          </div>
          
          <button type="submit" class="btn btn-primary">保存个人信息</button>
        </form>
      </div>
      
      <!-- 修改密码部分 -->
      <div class="section password-change">
        <h2>修改密码</h2>
        <form @submit.prevent="changePassword">
          <div class="form-group">
            <label for="currentPassword">当前密码</label>
            <input type="password" id="currentPassword" v-model="passwordForm.currentPassword" required />
          </div>
          
          <div class="form-group">
            <label for="newPassword">新密码</label>
            <input type="password" id="newPassword" v-model="passwordForm.newPassword" required />
            <div class="password-strength" :class="passwordStrengthClass">
              <div class="strength-meter"></div>
              <span>{{ passwordStrengthText }}</span>
            </div>
          </div>
          
          <div class="form-group">
            <label for="confirmPassword">确认新密码</label>
            <input 
              type="password" 
              id="confirmPassword" 
              v-model="passwordForm.confirmPassword" 
              required 
              :class="{ 'mismatch': isPasswordMismatch }" 
            />
            <small v-if="isPasswordMismatch" class="error">两次输入的密码不一致</small>
          </div>
          
          <button 
            type="submit" 
            class="btn btn-primary" 
            :disabled="isPasswordMismatch || passwordForm.newPassword.length < 6"
          >
            修改密码
          </button>
        </form>
      </div>
    </div>
    
    <!-- 提示信息 -->
    <div v-if="notification.show" class="notification" :class="notification.type">
      {{ notification.message }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserProfile',
  data() {
    return {
      userInfo: {
        username: '',
        fullName: '',
        email: '',
        department: '',
        position: ''
      },
      passwordForm: {
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      notification: {
        show: false,
        message: '',
        type: 'success'
      }
    };
  },
  computed: {
    isPasswordMismatch() {
      return this.passwordForm.newPassword !== this.passwordForm.confirmPassword 
             && this.passwordForm.confirmPassword !== '';
    },
    passwordStrength() {
      const password = this.passwordForm.newPassword;
      if (!password) return 0;
      
      let strength = 0;
      // 长度大于8加分
      if (password.length >= 8) strength += 1;
      // 包含数字加分
      if (/\d/.test(password)) strength += 1;
      // 包含小写字母加分
      if (/[a-z]/.test(password)) strength += 1;
      // 包含大写字母加分
      if (/[A-Z]/.test(password)) strength += 1;
      // 包含特殊字符加分
      if (/[^A-Za-z0-9]/.test(password)) strength += 1;
      
      return strength;
    },
    passwordStrengthClass() {
      const strength = this.passwordStrength;
      if (strength <= 1) return 'weak';
      if (strength <= 3) return 'medium';
      return 'strong';
    },
    passwordStrengthText() {
      const strength = this.passwordStrength;
      if (strength <= 1) return '弱';
      if (strength <= 3) return '中';
      return '强';
    }
  },
  mounted() {
    this.fetchUserInfo();
  },
  methods: {
    fetchUserInfo() {
      // 从本地存储或后端API获取用户信息
      const userId = localStorage.getItem('userId');
      const token = localStorage.getItem('token');
      
      if (!userId || !token) {
        this.$router.push('/login');
        return;
      }
      
      // 模拟API调用获取用户信息
      setTimeout(() => {
        // 这里应该替换为实际的API调用
        this.userInfo = {
          username: 'user123',
          fullName: '张三',
          email: 'zhangsan@example.com',
          department: '研发部',
          position: '软件工程师'
        };
      }, 300);
    },
    updateProfile() {
      // 模拟API调用更新用户信息
      setTimeout(() => {
        // 这里应该替换为实际的API调用
        this.showNotification('个人信息更新成功！', 'success');
        // 更新本地存储或状态管理中的用户信息
      }, 500);
    },
    changePassword() {
      if (this.isPasswordMismatch) {
        this.showNotification('两次输入的密码不一致', 'error');
        return;
      }
      
      if (this.passwordForm.newPassword.length < 6) {
        this.showNotification('密码长度不能小于6位', 'error');
        return;
      }
      
      // 模拟API调用修改密码
      setTimeout(() => {
        // 这里应该替换为实际的API调用
        if (this.passwordForm.currentPassword === 'wrongpassword') {
          this.showNotification('当前密码不正确', 'error');
          return;
        }
        
        this.showNotification('密码修改成功！', 'success');
        // 清空密码表单
        this.passwordForm = {
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        };
      }, 500);
    },
    showNotification(message, type = 'success') {
      this.notification = {
        show: true,
        message,
        type
      };
      
      // 3秒后自动关闭提示
      setTimeout(() => {
        this.notification.show = false;
      }, 3000);
    }
  }
};
</script>

<style scoped>
.user-profile {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px;
  position: relative;
}

.profile-header {
  margin-bottom: 30px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 15px;
}

.profile-header h1 {
  font-size: 24px;
  color: #333;
  margin: 0;
}

.profile-content {
  display: flex;
  flex-wrap: wrap;
  gap: 30px;
}

.section {
  flex: 1;
  min-width: 300px;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.section h2 {
  font-size: 18px;
  margin-top: 0;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #555;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:disabled {
  background-color: #f9f9f9;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 5px;
  color: #888;
  font-size: 12px;
}

.form-group .error {
  color: #e53935;
}

.form-group input.mismatch {
  border-color: #e53935;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-primary {
  background-color: #1976d2;
  color: white;
}

.btn-primary:hover {
  background-color: #1565c0;
}

.btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.password-strength {
  margin-top: 10px;
}

.password-strength .strength-meter {
  height: 5px;
  border-radius: 2px;
  margin-bottom: 5px;
}

.password-strength.weak .strength-meter {
  width: 30%;
  background-color: #f44336;
}

.password-strength.medium .strength-meter {
  width: 60%;
  background-color: #ff9800;
}

.password-strength.strong .strength-meter {
  width: 100%;
  background-color: #4caf50;
}

.password-strength span {
  font-size: 12px;
}

.password-strength.weak span {
  color: #f44336;
}

.password-strength.medium span {
  color: #ff9800;
}

.password-strength.strong span {
  color: #4caf50;
}

.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 4px;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  animation: fadeIn 0.3s, fadeOut 0.3s 2.7s;
}

.notification.success {
  background-color: #4caf50;
}

.notification.error {
  background-color: #f44336;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeOut {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-20px); }
}

@media (max-width: 768px) {
  .profile-content {
    flex-direction: column;
  }
  
  .section {
    width: 100%;
  }
}
</style> 