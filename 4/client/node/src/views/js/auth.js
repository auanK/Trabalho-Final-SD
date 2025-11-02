const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegisterLink = document.getElementById('show-register-link');
const showLoginLink = document.getElementById('show-login-link');

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

const loginBtn = document.getElementById('login-btn');
const loginErrorMsg = document.getElementById('login-error-msg');

loginBtn.addEventListener('click', () => {
    const nickname = document.getElementById('login-nickname').value;
    const password = document.getElementById('login-password').value;
    loginErrorMsg.innerText = "";

    if (!nickname || !password) {
        loginErrorMsg.innerText = "Nickname e senha são obrigatórios.";
        return;
    }

    window.electron.send('to-server', {
        command: "LOGIN",
        payload: {
            nickname: nickname,
            password: password
        }
    });
});

const registerBtn = document.getElementById('register-btn');
const registerMsg = document.getElementById('register-msg');

registerBtn.addEventListener('click', () => {
    const name = document.getElementById('register-name').value;
    const nickname = document.getElementById('register-nickname').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;

    registerMsg.innerText = "";
    registerMsg.style.color = '#d93025';

    if (!name || !nickname || !password) {
        registerMsg.innerText = "Todos os campos são obrigatórios.";
        return;
    }
    if (password !== confirmPassword) {
        registerMsg.innerText = "As senhas não coincidem.";
        return;
    }

    window.electron.send('to-server', {
        command: "REGISTER",
        payload: {
            nickname: nickname,
            name: name,
            password: password
        }
    });
});

window.electron.receive('from-server', (response) => {
    console.log("Recebido do servidor:", response);
    const command = response.command;
    const payload = response.payload;

    if (command === 'REGISTER_RESPONSE') {
        if (payload.success) {
            registerMsg.style.color = '#28a745';
            registerMsg.innerText = "Conta criada com sucesso! Faça o login.";
        } else {
            registerMsg.style.color = '#d93025';
            registerMsg.innerText = payload.message;
        }
    }

    if (command === 'LOGIN_RESPONSE') {
        if (payload.success) {
            localStorage.setItem('currentUserNickname', payload.nickname);
            window.electron.send('login-success');
        } else {
            loginErrorMsg.innerText = payload.message;
        }
    }
});

window.electron.receive('server-error', (errorMessage) => {
    console.error("Erro do servidor:", errorMessage);
    loginErrorMsg.innerText = "Erro de conexão com o servidor.";
    registerMsg.innerText = "Erro de conexão com o servidor.";
});