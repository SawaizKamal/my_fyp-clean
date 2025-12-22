import api from './config';

const authApi = {
  async register(username, password, email) {
    const response = await api.post('/auth/register', {
      username,
      password,
      email
    });
    return response.data;
  },

  async login(username, password) {
    const response = await api.post('/auth/login', {
      username,
      password
    });
    return response.data;
  },

  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  },

  logout() {
    // Token removal is handled by AuthContext
    return Promise.resolve();
  }
};

export default authApi;
