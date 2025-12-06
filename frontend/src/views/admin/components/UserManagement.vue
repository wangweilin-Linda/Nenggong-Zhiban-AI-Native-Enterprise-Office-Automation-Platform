<template>
  <div class="user-management">
    <div class="section-header">
      <h2>用户管理</h2>
      <button @click="showAddUserModal = true" class="add-user-btn">新增用户</button>
    </div>

    <div class="search-bar">
      <input 
        v-model="searchQuery" 
        placeholder="搜索用户名或邮箱" 
        @input="handleSearch"
      />
      <select v-model="filterDepartment">
        <option value="">所有部门</option>
        <option v-for="dept in departments" :key="dept.id" :value="dept.id">{{ dept.name }}</option>
      </select>
      <select v-model="filterStatus">
        <option value="">所有状态</option>
        <option value="active">活跃</option>
        <option value="inactive">已禁用</option>
      </select>
      <button @click="handleSearch" class="search-btn">搜索</button>
    </div>

    <div class="user-list">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>姓名</th>
            <th>邮箱</th>
            <th>部门</th>
            <th>职位</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td>{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.real_name }}</td>
            <td>{{ user.email }}</td>
            <td>{{ getDepartmentName(user.department_id) }}</td>
            <td>{{ getPositionName(user.position_id) }}</td>
            <td>
              <span :class="['status-badge', user.status === 'active' ? 'active' : 'inactive']">
                {{ user.status === 'active' ? '活跃' : '已禁用' }}
              </span>
            </td>
            <td>
              <button @click="editUser(user)" class="edit-btn">编辑</button>
              <button @click="confirmDeleteUser(user)" class="delete-btn">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination">
        <button 
          :disabled="currentPage === 1" 
          @click="currentPage--"
          class="page-btn"
        >
          上一页
        </button>
        <span class="page-info">第 {{ currentPage }} 页</span>
        <button 
          :disabled="!hasMorePages" 
          @click="currentPage++"
          class="page-btn"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 编辑用户弹窗 -->
    <div v-if="showEditModal" class="modal">
      <div class="modal-content">
        <h3>编辑用户</h3>
        
        <div class="form-item">
          <label>用户名</label>
          <input v-model="editingUser.username" disabled />
        </div>
        
        <div class="form-item">
          <label>姓名</label>
          <input v-model="editingUser.real_name" />
        </div>
        
        <div class="form-item">
          <label>邮箱</label>
          <input v-model="editingUser.email" type="email" />
        </div>
        
        <div class="form-item">
          <label>部门</label>
          <select v-model="editingUser.department_id">
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">{{ dept.name }}</option>
          </select>
        </div>
        
        <div class="form-item">
          <label>职位</label>
          <select v-model="editingUser.position_id">
            <option v-for="pos in positions" :key="pos.id" :value="pos.id">{{ pos.name }}</option>
          </select>
        </div>
        
        <div class="form-item">
          <label>状态</label>
          <select v-model="editingUser.status">
            <option value="active">活跃</option>
            <option value="inactive">禁用</option>
          </select>
        </div>
        
        <div class="modal-actions">
          <button @click="saveUser" class="save-btn">保存</button>
          <button @click="showEditModal = false" class="cancel-btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 新增用户弹窗 -->
    <div v-if="showAddUserModal" class="modal">
      <div class="modal-content">
        <h3>新增用户</h3>
        
        <div class="form-item">
          <label>用户名 <span class="required">*</span></label>
          <input v-model="newUser.username" />
        </div>
        
        <div class="form-item">
          <label>密码 <span class="required">*</span></label>
          <input type="password" v-model="newUser.password" />
        </div>
        
        <div class="form-item">
          <label>确认密码 <span class="required">*</span></label>
          <input type="password" v-model="newUser.confirmPassword" />
        </div>
        
        <div class="form-item">
          <label>姓名 <span class="optional">(可选)</span></label>
          <input v-model="newUser.real_name" placeholder="用户可在登录后设置" />
        </div>
        
        <div class="form-item">
          <label>邮箱 <span class="optional">(可选)</span></label>
          <input v-model="newUser.email" type="email" placeholder="用户可在登录后设置" />
        </div>
        
        <div class="form-item">
          <label>部门</label>
          <select v-model="newUser.department_id">
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">{{ dept.name }}</option>
          </select>
        </div>
        
        <div class="form-item">
          <label>职位</label>
          <select v-model="newUser.position_id">
            <option v-for="pos in positions" :key="pos.id" :value="pos.id">{{ pos.name }}</option>
          </select>
        </div>
        
        <div class="modal-actions">
          <button @click="addUser" class="save-btn">创建</button>
          <button @click="showAddUserModal = false" class="cancel-btn">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { message, Modal } from 'ant-design-vue';

export default {
  data() {
    return {
      users: [
        {
          id: 1,
          username: 'admin',
          real_name: '系统管理员',
          email: 'admin@example.com',
          department_id: 1,
          position_id: 1,
          status: 'active'
        }
      ],
      departments: [
        { id: 1, name: '行政部' },
        { id: 2, name: '财务部' },
        { id: 3, name: '人力资源部' },
        { id: 4, name: '市场部' },
        { id: 5, name: '研发部' }
      ],
      positions: [
        { id: 1, name: '总经理' },
        { id: 2, name: '部门经理' },
        { id: 3, name: '普通职员' }
      ],
      searchQuery: '',
      filterDepartment: '',
      filterStatus: '',
      showEditModal: false,
      showAddUserModal: false,
      currentPage: 1,
      pageSize: 10,
      editingUser: {
        id: null,
        username: '',
        real_name: '',
        email: '',
        department_id: null,
        position_id: null,
        status: 'active'
      },
      newUser: {
        username: '',
        password: '',
        confirmPassword: '',
        real_name: '',
        email: '',
        department_id: null,
        position_id: null,
        status: 'active'
      }
    };
  },
  computed: {
    filteredUsers() {
      let filtered = [...this.users];
      
      // 搜索过滤
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        filtered = filtered.filter(user => 
          user.username.toLowerCase().includes(query) ||
          user.email.toLowerCase().includes(query)
        );
      }
      
      // 部门过滤
      if (this.filterDepartment) {
        filtered = filtered.filter(user => user.department_id === this.filterDepartment);
      }
      
      // 状态过滤
      if (this.filterStatus) {
        filtered = filtered.filter(user => user.status === this.filterStatus);
      }
      
      // 分页
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      return filtered.slice(start, end);
    },
    hasMorePages() {
      return this.filteredUsers.length === this.pageSize;
    }
  },
  mounted() {
    this.fetchUsers();
    this.fetchDepartments();
    this.fetchPositions();
    
    // 检查是否有来自AI助手的用户创建请求
    this.checkUserCreationRequest();
    
    // 添加事件监听器处理用户创建请求
    window.addEventListener('user-create-request', this.handleUserCreateRequest);
  },
  beforeUnmount() {
    // 移除事件监听器
    window.removeEventListener('user-create-request', this.handleUserCreateRequest);
  },
  methods: {
    // 检查localStorage中是否存在用户创建数据
    checkUserCreationRequest() {
      try {
        console.log('检查是否有用户创建请求数据...');
        const userCreationDataStr = localStorage.getItem('user_creation_data');
        if (userCreationDataStr) {
          console.log('从localStorage中找到用户创建数据:', userCreationDataStr);
          try {
          const userData = JSON.parse(userCreationDataStr);
            console.log('解析后的用户创建数据:', userData);
          
          if (userData && userData.action === 'create_user') {
              console.log('有效的用户创建请求，准备填充表单');
            // 将数据预填充到新用户表单中
            this.fillUserForm(userData);
            
            // 清除localStorage中的数据
            localStorage.removeItem('user_creation_data');
              console.log('已从localStorage中清除用户创建数据');
            
            // 显示新增用户弹窗
            this.showAddUserModal = true;
              console.log('已显示新增用户弹窗');
            } else {
              console.log('用户创建数据无效或不是创建用户操作:', userData);
          }
          } catch (parseError) {
            console.error('解析用户创建数据失败:', parseError);
          }
        } else {
          console.log('未找到用户创建数据');
        }
      } catch (error) {
        console.error('检查用户创建请求失败:', error);
      }
    },
    
    // 处理用户创建请求事件
    handleUserCreateRequest(event) {
      console.log('收到用户创建请求事件:', event.detail);
      try {
      if (event.detail && event.detail.action === 'create_user') {
          console.log('有效的用户创建请求事件，准备填充表单');
        this.fillUserForm(event.detail);
        this.showAddUserModal = true;
          console.log('已显示新增用户弹窗');
        } else {
          console.log('用户创建请求事件无效或不是创建用户操作:', event.detail);
        }
      } catch (error) {
        console.error('处理用户创建请求事件失败:', error);
      }
    },
    
    // 填充用户表单
    fillUserForm(userData) {
      console.log('开始填充用户表单:', userData);
      try {
      // 根据userData中的数据填充新用户表单
      this.newUser.username = userData.username || '';
      this.newUser.password = userData.password || '';
      this.newUser.confirmPassword = userData.password || '';
      
      // 设置部门
      if (userData.department) {
          console.log('设置部门:', userData.department);
        // 查找或创建部门
        const deptName = userData.department;
        let deptId = null;
        
        // 查找匹配的部门
        const existingDept = this.departments.find(dept => 
          dept.name.toLowerCase() === deptName.toLowerCase()
        );
        
        if (existingDept) {
            console.log('找到匹配的部门:', existingDept);
          deptId = existingDept.id;
        } else {
            console.log('未找到匹配的部门，使用默认部门');
          // 如果没找到匹配的部门，使用默认部门(第一个)
          deptId = this.departments.length > 0 ? this.departments[0].id : null;
        }
        
        this.newUser.department_id = deptId;
      }
      
        // 设置角色/职位
        if (userData.role) {
          console.log('设置角色:', userData.role);
          // 查找匹配的职位
          const roleMapping = {
            '普通用户': '普通职员',
            '管理员': '部门经理',
            '超级管理员': '总经理'
          };
          
          const positionName = roleMapping[userData.role] || '普通职员';
          const position = this.positions.find(p => p.name === positionName);
          
          if (position) {
            console.log('找到匹配的职位:', position);
            this.newUser.position_id = position.id;
          } else {
            console.log('未找到匹配的职位，使用默认职位');
            // 默认使用最后一个职位（通常是普通职员）
            this.newUser.position_id = this.positions.length > 0 ? this.positions[this.positions.length - 1].id : null;
          }
        } else {
      // 设置默认职位
      this.newUser.position_id = this.positions.length > 0 ? this.positions[this.positions.length - 1].id : null;
        }
        
        console.log('用户表单填充完成:', this.newUser);
      } catch (error) {
        console.error('填充用户表单失败:', error);
      }
    },
    async fetchUsers() {
      try {
        console.log('开始获取所有用户数据');
        this.loading = true;
        let allUsers = [];
        
        // 1. 开发环境：从所有可能的存储位置获取用户数据
        if (process.env.NODE_ENV === 'development') {
          // 从local_users获取
          try {
            const localUsersStr = localStorage.getItem('local_users');
            if (localUsersStr) {
              const localUsers = JSON.parse(localUsersStr);
              if (Array.isArray(localUsers)) {
                console.log(`从local_users加载了${localUsers.length}个用户`);
                allUsers = [...allUsers, ...localUsers];
              }
            }
          } catch (e) {
            console.error('从local_users获取用户数据失败:', e);
          }
          
          // 从mock_users获取
          try {
            const mockUsersStr = localStorage.getItem('mock_users');
            if (mockUsersStr) {
              const mockUsers = JSON.parse(mockUsersStr);
              if (Array.isArray(mockUsers)) {
                console.log(`从mock_users加载了${mockUsers.length}个用户`);
                allUsers = [...allUsers, ...mockUsers];
              }
            }
          } catch (e) {
            console.error('从mock_users获取用户数据失败:', e);
          }
          
          // 从user_store获取
          try {
            const userStoreStr = localStorage.getItem('user_store');
            if (userStoreStr) {
              const userStore = JSON.parse(userStoreStr);
              if (userStore && Array.isArray(userStore.users)) {
                console.log(`从user_store加载了${userStore.users.length}个用户`);
                allUsers = [...allUsers, ...userStore.users];
              }
            }
          } catch (e) {
            console.error('从user_store获取用户数据失败:', e);
          }
          
          // 从user数组获取
          try {
            const usersStr = localStorage.getItem('users');
            if (usersStr) {
              const users = JSON.parse(usersStr);
              if (Array.isArray(users)) {
                console.log(`从users加载了${users.length}个用户`);
                allUsers = [...allUsers, ...users];
              }
            }
          } catch (e) {
            console.error('从users获取用户数据失败:', e);
          }
          
          // 获取当前登录用户并确保也加入列表
          try {
            const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
            if (userStr) {
              const currentUser = JSON.parse(userStr);
              if (currentUser && currentUser.id) {
                console.log('从当前登录用户获取用户数据');
                // 检查是否已包含该用户
                if (!allUsers.some(u => u.id == currentUser.id)) {
                  allUsers.push({
                    id: currentUser.id,
                    username: currentUser.username,
                    real_name: currentUser.real_name || currentUser.full_name || currentUser.username,
                    email: currentUser.email || `${currentUser.username}@example.com`,
                    department_id: currentUser.department_id || 1,
                    position_id: currentUser.position_id || 1,
                    status: 'active'
                  });
                }
              }
            }
          } catch (e) {
            console.error('获取当前登录用户数据失败:', e);
          }
          
          // 去重处理
          const uniqueUsers = [];
          const userIds = new Set();
          
          for (const user of allUsers) {
            if (user && user.id && !userIds.has(user.id)) {
              userIds.add(user.id);
              uniqueUsers.push(user);
            } else if (user && user.username && !uniqueUsers.some(u => u.username === user.username)) {
              // 如果没有ID但有用户名，以用户名为唯一标识
              uniqueUsers.push(user);
            }
          }
          
          console.log(`总共找到${uniqueUsers.length}个唯一用户`);
          
          // 确保至少有默认管理员
          if (uniqueUsers.length === 0) {
            uniqueUsers.push({
              id: 1,
              username: 'admin',
              real_name: '系统管理员',
              email: 'admin@example.com',
              department_id: 1,
              position_id: 1,
              status: 'active'
            });
          }
          
          this.users = uniqueUsers;
          this.loading = false;
          return;
        }

        // 2. 非开发环境：尝试API请求
        const token = localStorage.getItem('token');
        const response = await axios.get('/api/admin/users', {
          params: {
            search: this.searchQuery || undefined,
            department_id: this.filterDepartment || undefined,
            status: this.filterStatus || undefined,
            skip: (this.currentPage - 1) * this.pageSize,
            limit: this.pageSize
          },
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.data) {
          this.users = response.data;
        }
      } catch (error) {
        console.error('获取用户列表失败:', error);
        // 在API调用失败时尝试加载本地数据
        try {
          // 首先检查local_users
          const localUsersStr = localStorage.getItem('local_users');
          if (localUsersStr) {
            const localUsers = JSON.parse(localUsersStr);
            if (Array.isArray(localUsers) && localUsers.length > 0) {
              this.users = localUsers;
              console.log('API失败，成功从local_users加载数据，数量:', localUsers.length);
              message.warning('获取用户列表失败，使用本地存储数据');
              return;
            }
          }
          
          // 然后检查mock_users
          const mockUsersStr = localStorage.getItem('mock_users');
          if (mockUsersStr) {
            const mockUsers = JSON.parse(mockUsersStr);
            if (Array.isArray(mockUsers) && mockUsers.length > 0) {
              this.users = mockUsers;
              console.log('API失败，成功从mock_users加载数据，数量:', mockUsers.length);
              message.warning('获取用户列表失败，使用本地存储数据');
              return;
            }
          }
          
          // 如果都没有，确保用户至少看到默认数据
          if (!this.users || this.users.length === 0) {
            this.users = [
              {
                id: 1,
                username: 'admin',
                real_name: '系统管理员',
                email: 'admin@example.com',
                department_id: 1,
                position_id: 1,
                status: 'active'
              }
            ];
            console.log('使用默认用户数据');
          }
        } catch (localError) {
          console.error('加载本地用户数据失败:', localError);
        }
        message.error('获取用户列表失败，使用默认数据');
      } finally {
        this.loading = false;
      }
    },
    async fetchDepartments() {
      try {
        const response = await axios.get('/api/admin/departments', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        // 如果API调用成功，使用API返回的数据
        if (response.data && response.data.length > 0) {
          this.departments = response.data;
        }
      } catch (error) {
        console.error('获取部门列表失败:', error);
        message.error('获取部门列表失败，使用默认数据');
        // 使用默认部门数据
      }
    },
    async fetchPositions() {
      try {
        const response = await axios.get('/api/admin/positions', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        // 如果API调用成功，使用API返回的数据
        if (response.data && response.data.length > 0) {
          this.positions = response.data;
        }
      } catch (error) {
        console.error('获取职位列表失败:', error);
        message.error('获取职位列表失败，使用默认数据');
        // 使用默认职位数据
      }
    },
    getDepartmentName(id) {
      const dept = this.departments.find(d => d.id === id);
      return dept ? dept.name : '未分配';
    },
    getPositionName(id) {
      const pos = this.positions.find(p => p.id === id);
      return pos ? pos.name : '未分配';
    },
    handleSearch() {
      this.currentPage = 1; // 重置页码
    },
    editUser(user) {
      this.editingUser = { ...user };
      this.showEditModal = true;
    },
    async saveUser() {
      try {
        // 验证用户ID
        if (!this.editingUser.id) {
          message.error('用户ID无效');
          console.error('用户ID无效:', this.editingUser);
          return;
        }
        
        // 确保ID是数字类型
        const userId = parseInt(this.editingUser.id);
        if (isNaN(userId)) {
          message.error('用户ID格式错误');
          console.error('用户ID不是数字:', this.editingUser.id);
          return;
        }
        
        const token = localStorage.getItem('token');
        
        // 检查token是否存在
        if (!token) {
          message.error('未登录，请先登录');
          return;
        }
        
        // 检查是否为模拟环境
        if (token.includes('mock_')) {
          // 更新本地数组中的用户
          const index = this.users.findIndex(u => u.id === userId);
          if (index !== -1) {
            this.users[index] = { ...this.editingUser, id: userId };
            this.showEditModal = false;
            message.success('用户信息更新成功');
          }
          return;
        }

        // 准备更新的数据
        const userData = {
          real_name: this.editingUser.real_name || '',
          email: this.editingUser.email || '',
          department_id: this.editingUser.department_id,
          position_id: this.editingUser.position_id,
          status: this.editingUser.status || 'active'
        };

        console.log(`准备更新用户 ${userId}:`, userData);

        const response = await axios.put(`/api/admin/users/${userId}`, userData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        console.log('用户更新成功:', response.data);
        this.showEditModal = false;
        this.fetchUsers();
        message.success('用户信息更新成功');
      } catch (error) {
        console.error('保存用户失败:', error);
        if (error.response) {
          if (error.response.status === 401) {
            message.error('未授权，请重新登录');
          } else if (error.response.status === 404) {
            message.error('用户不存在');
          } else {
            message.error(error.response.data?.detail || '保存用户失败');
          }
        } else {
          message.error('保存用户失败: ' + error.message);
        }
      }
    },
    async addUser() {
      console.log('addUser方法被调用');
      console.log('this.users的类型:', typeof this.users, '是否是数组:', Array.isArray(this.users));
      
      // 表单验证 - 只验证用户名和密码
      if (!this.newUser.username || !this.newUser.password) {
        message.error('请填写用户名和密码');
        return;
      }
      
      if (this.newUser.password !== this.newUser.confirmPassword) {
        message.error('两次输入的密码不一致');
        return;
      }

      try {
        // 创建用户对象
        const newUser = {
          id: Array.isArray(this.users) ? Math.max(...this.users.map(u => parseInt(u.id || 0)), 0) + 1 : 1,
          username: this.newUser.username,
          real_name: this.newUser.real_name || '', // 允许为空
          email: this.newUser.email || '', // 允许为空
          department_id: this.newUser.department_id || 1,
          position_id: this.newUser.position_id || 3,
          status: 'active',
          created_at: new Date().toISOString(),
          _persistent: true // 确保数据持久化
        };
        
        console.log('准备创建的新用户数据:', newUser);
        
        // 确保this.users是数组
        if (!Array.isArray(this.users)) {
          console.warn('this.users不是数组，正在初始化为空数组');
          this.users = [];
        }
        
        // 检查用户名是否已存在
        if (this.users.some(u => u.username === newUser.username)) {
          message.error('用户名已存在');
          return;
        }
        
        try {
          // 1. 使用API保存用户
          console.log('尝试使用API创建用户');
          const response = await axios.post('/api/admin/users', {
            username: newUser.username,
            password: this.newUser.password,
            real_name: newUser.real_name,
            email: newUser.email,
            department_id: newUser.department_id,
            position_id: newUser.position_id,
            status: newUser.status,
            _persistent: true // 确保持久化标记
          }, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });
          
          console.log('API创建用户响应:', response);
          
          if (response && response.data) {
            console.log('API创建用户成功');
            // 如果API返回了用户ID，使用API返回的ID
            if (response.data.id) {
              newUser.id = response.data.id;
            }
          }
        } catch (apiError) {
          console.error('API创建用户失败, 尝试本地存储:', apiError);
        }
        
        // 2. 添加到本地数组（UI显示用）
        this.users.push(newUser);
        console.log('已添加用户到本地数组:', this.users.length);
        
        // 3. 保存到local_users（确保持久化）
        try {
          // 读取现有用户
          let localUsers = [];
          try {
            const localUsersStr = localStorage.getItem('local_users');
            if (localUsersStr) {
              localUsers = JSON.parse(localUsersStr);
              if (!Array.isArray(localUsers)) {
                console.warn('local_users不是数组，重置为空数组');
                localUsers = [];
              }
            }
          } catch (parseError) {
            console.error('解析local_users失败:', parseError);
            localUsers = [];
          }
          
          // 确认用户数据不存在
          const existingIndex = localUsers.findIndex(u => u.id === newUser.id || u.username === newUser.username);
          if (existingIndex >= 0) {
            console.log('用户已存在于local_users中，更新数据');
            localUsers[existingIndex] = {...newUser, _persistent: true};
          } else {
            console.log('将新用户添加到local_users');
            localUsers.push({...newUser, _persistent: true});
          }
          
          // 保存回local_users
          localStorage.setItem('local_users', JSON.stringify(localUsers));
          localStorage.setItem('persist_users', 'true'); // 设置永久保存标志
          console.log('已保存到local_users, 共计:', localUsers.length);
        } catch (storageError) {
          console.error('保存到local_users失败:', storageError);
        }
        
        // 4. 保存到mock_users（兼容性）
        try {
          let mockUsers = [];
          try {
            const mockUsersStr = localStorage.getItem('mock_users');
            if (mockUsersStr) {
              mockUsers = JSON.parse(mockUsersStr);
              if (!Array.isArray(mockUsers)) {
                mockUsers = [];
              }
            }
          } catch (parseError) {
            console.error('解析mock_users失败:', parseError);
            mockUsers = [];
          }
          
          // 添加到mock_users
          mockUsers.push({
            ...newUser,
            password: this.newUser.password, // 仅用于开发环境
            _persistent: true
          });
          
          localStorage.setItem('mock_users', JSON.stringify(mockUsers));
          localStorage.setItem('using_local_users', 'true');
          console.log('已保存到mock_users, 共计:', mockUsers.length);
        } catch (mockError) {
          console.error('保存到mock_users失败:', mockError);
        }
        
        // 5. 验证保存结果
        try {
          const verifyLocalUsers = localStorage.getItem('local_users');
          const verifyMockUsers = localStorage.getItem('mock_users');
          console.log('验证结果 - local_users存在:', !!verifyLocalUsers, 'mock_users存在:', !!verifyMockUsers);
          
          if (!verifyLocalUsers && !verifyMockUsers) {
            console.error('验证失败: 未能保存到任何存储位置');
            message.warning('用户创建可能未成功持久化，但已添加到当前界面');
          }
        } catch (verifyError) {
          console.error('验证保存结果失败:', verifyError);
        }
        
        // 显示成功消息
        message.success('用户创建成功');
        
        // 关闭模态框和重置表单
        this.showAddUserModal = false;
        this.newUser = {
          username: '',
          password: '',
          confirmPassword: '',
          real_name: '',
          email: '',
          department_id: null,
          position_id: null,
          status: 'active'
        };
      } catch (error) {
        console.error('创建用户过程中出错:', error);
        message.error('创建用户失败: ' + (error.message || '未知错误'));
      }
    },
    confirmDeleteUser(user) {
      if (!Modal) {
        // 如果Modal未定义，使用原生确认
        if (confirm(`确定要删除用户 ${user.username} 吗？此操作不可恢复。`)) {
          this.deleteUser(user.id);
        }
      } else {
        Modal.confirm({
          title: '确认删除',
          content: `确定要删除用户 ${user.username} 吗？此操作不可恢复。`,
          okText: '确认',
          cancelText: '取消',
          onOk: () => this.deleteUser(user.id)
        });
      }
    },
    deleteUser(userId) {
      console.log('开始删除用户:', userId);
      this.loading = true;
      
      // 在开发环境中直接处理本地存储操作
      if (process.env.NODE_ENV === 'development') {
        console.log('开发环境: 在本地存储中删除用户');
        
        try {
          let deletedFromLocalStorage = false;
          
          // 1. 从local_users中删除
          try {
            const localUsersStr = localStorage.getItem('local_users');
            if (localUsersStr) {
              const localUsers = JSON.parse(localUsersStr);
              // 记录原始长度
              const originalLength = localUsers.length;
              // 过滤掉要删除的用户
              const filteredUsers = localUsers.filter(user => user.id != userId);
              // 如果长度变化，说明找到并删除了
              if (filteredUsers.length < originalLength) {
                localStorage.setItem('local_users', JSON.stringify(filteredUsers));
                console.log('从local_users中删除用户成功');
                deletedFromLocalStorage = true;
              }
            }
          } catch (e) {
            console.error('从local_users删除用户失败:', e);
          }
          
          // 2. 从mock_users中删除
          try {
            const mockUsersStr = localStorage.getItem('mock_users');
            if (mockUsersStr) {
              const mockUsers = JSON.parse(mockUsersStr);
              const originalLength = mockUsers.length;
              const filteredUsers = mockUsers.filter(user => user.id != userId);
              if (filteredUsers.length < originalLength) {
                localStorage.setItem('mock_users', JSON.stringify(filteredUsers));
                console.log('从mock_users中删除用户成功');
                deletedFromLocalStorage = true;
              }
            }
          } catch (e) {
            console.error('从mock_users删除用户失败:', e);
          }
          
          // 3. 从界面列表中删除
          this.users = this.users.filter(user => user.id != userId);
          console.log('从界面列表中删除用户成功');
          
          // 显示成功消息
          message.success(deletedFromLocalStorage 
            ? '用户删除成功（本地存储）' 
            : '用户从界面移除成功，但未找到本地存储数据');
        } catch (err) {
          console.error('删除用户过程中出错:', err);
          message.error('删除用户失败: ' + err.message);
        } finally {
          this.loading = false;
        }
        return;
      }
      
      // 生产环境使用API
      axios.delete(`/api/admin/users/${userId}`)
        .then(response => {
          message.success('用户删除成功');
          // 从当前用户列表中移除
          this.users = this.users.filter(user => user.id !== userId);
        })
        .catch(error => {
          console.error('删除用户失败:', error);
          message.error('删除用户失败: ' + (error.response?.data?.message || '未知错误'));
        })
        .finally(() => {
          this.loading = false;
        });
    }
  }
};
</script>

<style scoped>
.user-management {
  padding: 20px;
  background: white;
  margin: 20px;
  border-radius: 4px;
  overflow: auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  margin: 0;
}

.add-user-btn {
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-bar input, 
.search-bar select {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.search-btn {
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.user-list table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

.user-list th, 
.user-list td {
  border: 1px solid #d9d9d9;
  padding: 12px;
  text-align: left;
}

.user-list th {
  background-color: #f5f5f5;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.active {
  background-color: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.status-badge.inactive {
  background-color: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffa39e;
}

.edit-btn, 
.delete-btn {
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 8px;
}

.edit-btn {
  background-color: #1890ff;
  color: white;
  border: none;
}

.delete-btn {
  background-color: #ff4d4f;
  color: white;
  border: none;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 4px;
  width: 500px;
  max-width: 90%;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
}

.form-item input,
.form-item select {
  width: 100%;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.save-btn,
.cancel-btn {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.save-btn {
  background-color: #1890ff;
  color: white;
  border: none;
}

.cancel-btn {
  background-color: #f5f5f5;
  border: 1px solid #d9d9d9;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.page-btn {
  padding: 4px 8px;
  border: 1px solid #d9d9d9;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.page-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.page-info {
  color: #666;
}

.form-item .required {
  color: #ff4d4f;
  margin-left: 4px;
}

.form-item .optional {
  color: #999;
  font-size: 12px;
  margin-left: 4px;
}
</style> 