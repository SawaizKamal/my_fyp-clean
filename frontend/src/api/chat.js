import api from './config';

const chatApi = {
  async chat(message, code = null) {
    const response = await api.post('/chat', {
      message,
      code
    });
    return response.data;
  }
};

export default chatApi;
