const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegisterLink = document.getElementById('show-register-link');
const showLoginLink = document.getElementById('show-login-link');

// Logica para alternar
showRegisterLink.addEventListener('click', (e) => {
    e.preventDefault();
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
});
showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    registerForm.style.display = 'none';
    loginForm.style.display = 'block';
});

// Login 
const loginBtn = document.getElementById('login-btn');
const loginErrorMsg = document.getElementById('login-error-msg');

loginBtn.addEventListener('click', async () => { 
    const nickname = document.getElementById('login-nickname').value;
    const password = document.getElementById('login-password').value;
    loginErrorMsg.innerText = "";

    if (!nickname || !password) {
        loginErrorMsg.innerText = "Nickname e senha são obrigatórios.";
        return;
    }

    try {
        const [success, message, token] = await window.api.callRMI('login', [nickname, password]);

        if (success) {
            localStorage.setItem('currentUserNickname', nickname);
            localStorage.setItem('sessionToken', token); 
            window.api.send('login-success'); 
        } else {
            loginErrorMsg.innerText = message;
        }
    } catch (error) {
        loginErrorMsg.innerText = `Erro de conexão: ${error.message}`;
    }
});

// Registro
const registerBtn = document.getElementById('register-btn');
const registerMsg = document.getElementById('register-msg');

registerBtn.addEventListener('click', async () => { 
    const name = document.getElementById('register-name').value;
    const nickname = document.getElementById('register-nickname').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;

    registerMsg.innerText = "";
    registerMsg.style.color = '#d93025';

    // Validação de campos
    if (!name || !nickname || !password) {
        registerMsg.innerText = "Todos os campos são obrigatórios.";
        return;
    }
    if (password !== confirmPassword) {
        registerMsg.innerText = "As senhas não coincidem.";
        return;
    }

    try {
        const [success, message] = await window.api.callRMI('register', [nickname, name, password]);
        
        if (success) {
            registerMsg.style.color = '#28a745';
            registerMsg.innerText = "Conta criada com sucesso! Faça o login.";
        } else {
            registerMsg.style.color = '#d93025';
            registerMsg.innerText = message;
        }
    } catch (error) {
        registerMsg.innerText = `Erro de conexão: ${error.message}`;
    }
});

// Tratamento de erros de conexão 
window.api.receive('server-error', (errorMessage) => {
    console.error("Erro do servidor:", errorMessage);
    loginErrorMsg.innerText = "Erro de conexão com o servidor.";
    registerMsg.innerText = "Erro de conexão com o servidor.";
});