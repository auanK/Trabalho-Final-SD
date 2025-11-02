// Elementos do DOM
const contactList = document.getElementById('contact-list');
const loggedInUserNickname = document.getElementById('user-nickname');
const addContactBtn = document.getElementById('add-contact-btn');
const logoutBtn = document.getElementById('logout-btn');

// Áudio
const ringtoneSound = document.getElementById('ringtone-sound');
const dialingSound = document.getElementById('dialing-sound');
const hangupSound = document.getElementById('hangup-sound');

// Chamada Recebida
const incomingCallDialog = document.getElementById('incoming-call-dialog');
const callerIdLabel = document.getElementById('caller-id-label');
const acceptCallBtn = document.getElementById('accept-call-btn');
const refuseCallBtn = document.getElementById('refuse-call-btn');

// Adicionar Contato
const addContactDialog = document.getElementById('add-contact-dialog');
const searchNicknameInput = document.getElementById('search-nickname-input');
const searchContactBtn = document.getElementById('search-contact-btn');
const searchResultArea = document.getElementById('search-result-area');
const foundContactNickname = document.getElementById('found-contact-nickname');
const sendRequestBtn = document.getElementById('send-request-btn');
const searchErrorMsg = document.getElementById('search-error-msg');

// Janela de Chamada
const callWindowDialog = document.getElementById('call-window-dialog');
const outgoingCallState = document.getElementById('outgoing-call-state');
const outgoingCallLabel = document.getElementById('outgoing-call-label');
const cancelCallBtn = document.getElementById('cancel-call-btn');
const activeCallState = document.getElementById('active-call-state');
const activeCallLabel = document.getElementById('active-call-label');
const endCallBtn = document.getElementById('end-call-btn');

// Estado da Aplicação
const state = {
    currentUser: localStorage.getItem('currentUserNickname') || 'user_error',
    contacts: new Map(),
    currentCall: {
        nickname: null,
        status: 'idle'
    }
};
loggedInUserNickname.innerText = state.currentUser;

// Renderizando a lista de contatos
function renderContacts() {
    contactList.innerHTML = '';
    for (const contact of state.contacts.values()) {
        const statusClass = (contact.status || 'Offline').toLowerCase().replace(' ', '-');
        const contactItem = document.createElement('li');
        contactItem.innerHTML = `
        <div class="contact-info">
            <span class="status-indicator ${statusClass}"></span>
            <span class="contact-nickname">${contact.nickname}</span>
        </div>
        <button class="call-btn" data-nickname="${contact.nickname}" ${contact.status !== 'Online' ? 'disabled' : ''}>Ligar</button>
        `;
        contactList.appendChild(contactItem);
    }
    addCallButtonListeners();
}


function showDialog(dialogElement) { dialogElement.style.display = 'flex'; }
function hideDialog(dialogElement) { dialogElement.style.display = 'none'; }

function searchContact() {
    const nicknameToSearch = searchNicknameInput.value;
    searchErrorMsg.innerText = '';
    searchResultArea.style.display = 'none';
    if (!nicknameToSearch) {
        searchErrorMsg.innerText = 'Por favor, digite um nickname.';
        return;
    }
    window.electron.send('to-server', {
        command: 'SEARCH_USER',
        payload: { nickname_query: nicknameToSearch }
    });
}

function initiateCall(calleeNickname) {
    console.log(`Iniciando chamada para ${calleeNickname}`);
    state.currentCall.nickname = calleeNickname;
    state.currentCall.status = 'outgoing';

    outgoingCallLabel.innerText = `A ligar para ${calleeNickname}...`;
    outgoingCallState.style.display = 'block';
    activeCallState.style.display = 'none';
    showDialog(callWindowDialog);

    dialingSound.play();

    window.electron.send('to-server', {
        command: 'INVITE',
        payload: { target_nickname: calleeNickname }
    });
}

function stopAllCallSounds() {
    ringtoneSound.pause();
    ringtoneSound.currentTime = 0;
    dialingSound.pause();
    dialingSound.currentTime = 0;
}

function resetAddContactDialog() {
    searchNicknameInput.value = '';
    searchResultArea.style.display = 'none';
    searchErrorMsg.innerText = '';
}

function endCurrentCall() {
    console.log("Encerrando chamada localmente.");
    stopAllCallSounds();
    hideDialog(callWindowDialog);
    hideDialog(incomingCallDialog);
    hangupSound.play();

    if (state.currentCall.status === 'active') {
        console.log("Parando motor VoIP C++.");
        const result = window.voip.stopCall();
        if (!result.success) {
            console.error("Falha ao parar C++:", result.error);
        }
    }

    state.currentCall.nickname = null;
    state.currentCall.status = 'idle';
}

function handleFriendRequest(from_nickname) {
    setTimeout(() => {
        const accepted = confirm(`${from_nickname} quer te adicionar como amigo. Aceitar?`);

        if (accepted) {
            window.electron.send('to-server', {
                command: 'ACCEPT_FRIEND',
                payload: { requester_nickname: from_nickname }
            });
        } else {
            window.electron.send('to-server', {
                command: 'REJECT_FRIEND',
                payload: { requester_nickname: from_nickname }
            });
        }
    }, 500);
}

addContactBtn.addEventListener('click', () => showDialog(addContactDialog));

logoutBtn.addEventListener('click', () => {
    console.log("Enviando pedido 'quit-app' para o main.js");
    window.electron.send('quit-app');
});

acceptCallBtn.addEventListener('click', () => {
    console.log("Botão 'Aceitar' clicado.");
    stopAllCallSounds();
    hideDialog(incomingCallDialog);

    window.electron.send('to-server', {
        command: 'ACCEPT',
        payload: { caller_nickname: state.currentCall.nickname }
    });
});

refuseCallBtn.addEventListener('click', () => {
    console.log("Botão 'Recusar' clicado.");
    window.electron.send('to-server', {
        command: 'REJECT',
        payload: { caller_nickname: state.currentCall.nickname }
    });
    endCurrentCall();
});

searchContactBtn.addEventListener('click', searchContact);

sendRequestBtn.addEventListener('click', () => {
    const targetNickname = foundContactNickname.innerText;
    if (targetNickname) {
        console.log(`Enviando pedido de amizade para ${targetNickname}`);
        window.electron.send('to-server', {
            command: 'ADD_FRIEND',
            payload: { target_nickname: targetNickname }
        });
    }
});

addContactDialog.addEventListener('click', (e) => {
    if (e.target === addContactDialog) {
        hideDialog(addContactDialog);
        resetAddContactDialog();
    }
});

cancelCallBtn.addEventListener('click', () => {
    console.log("Botão 'Cancelar' (outgoing) clicado.");
    window.electron.send('to-server', { command: 'BYE', payload: {} });
    endCurrentCall();
});

endCallBtn.addEventListener('click', () => {
    console.log("Botão 'Desligar' (active) clicado.");
    window.electron.send('to-server', { command: 'BYE', payload: {} });
    endCurrentCall();
});

function addCallButtonListeners() {
    document.querySelectorAll('.call-btn').forEach(button => {
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        if (!newButton.disabled) {
            newButton.addEventListener('click', () => {
                const nickname = newButton.dataset.nickname;
                initiateCall(nickname);
            });
        }
    });
}

// VoIP C++ Event Handler
function onVoipEvent(event) {
    console.log(`[EVENTO DO C++ (VoIP)]: Tipo = ${event.type}`);

    if (event.type === 'notification') {
        try {
            const data = JSON.parse(event.data);
            console.log("  -> Notificação (JSON do Relay):", data);
        } catch (e) {
            console.warn("  -> Recebido JSON inválido do C++ (Relay):", event.data);
        }
    } else if (event.type === 'error') {
        console.error("  -> ERRO DO C++ (VoIP Engine):", event.data);
        alert(`Erro crítico de áudio: ${event.data}`);
        endCurrentCall();
    } else if (event.type === 'stopped') {
        console.log("  -> C++ confirmou parada de VoIP:", event.data);
        state.currentCall.status = 'idle';
    }
}

// Iniciando Sessão VoIP
function startVoipSession(callData) {
    if (state.currentCall.status === 'active') {
        console.warn("[UI] Já estava em chamada, ignorando startVoipSession.");
        return;
    }

    console.log("Iniciando motor VoIP C++ com dados:", callData);

    const voipOptions = {
        relay_server: {
            ip: callData.relay_ip,
            port: callData.relay_port
        },
        session_id: callData.token,
        my_user_info_json: JSON.stringify({ userId: callData.callee_nickname })
    };

    const result = window.voip.startCall(voipOptions, onVoipEvent);

    if (result.success) {
        console.log("Motor VoIP C++ iniciado com sucesso!");
        state.currentCall.status = 'active';

        stopAllCallSounds();

        activeCallLabel.innerText = `Em chamada com ${state.currentCall.nickname}`;
        outgoingCallState.style.display = 'none';
        activeCallState.style.display = 'block';
        showDialog(callWindowDialog);

    } else {
        console.error("FALHA ao iniciar o motor VoIP C++:", result.error);
        alert(`Erro ao iniciar áudio: ${result.error}`);
    }
}


// Recebendo respostas do servidor (passaram primeiro por main.js)
window.electron.receive('from-server', (response) => {
    console.log("Recebido do Servidor:", response);
    const command = response.command;
    const payload = response.payload;

    const processFriendRequest = (from_nickname) => {
        const accepted = confirm(`${from_nickname} quer te adicionar como amigo. Aceitar?`);

        if (accepted) {
            window.electron.send('to-server', {
                command: 'ACCEPT_FRIEND',
                payload: { requester_nickname: from_nickname }
            });
        } else {
            window.electron.send('to-server', {
                command: 'REJECT_FRIEND',
                payload: { requester_nickname: from_nickname }
            });
        }
    };

    // Lidando com diferentes comandos do servidor
    switch (command) {
        case 'FRIEND_LIST':
            state.contacts.clear();
            for (const friend of payload.friends) {
                state.contacts.set(friend.nickname, friend);
            }
            renderContacts();
            break;

        case 'STATUS_UPDATE':
            if (state.contacts.has(payload.nickname)) {
                state.contacts.get(payload.nickname).status = payload.status;
                renderContacts();
            }
            break;

        case 'SEARCH_RESPONSE':
            if (payload.success && payload.results.length > 0) {
                const foundUser = payload.results[0];
                foundContactNickname.innerText = foundUser.nickname;
                searchResultArea.style.display = 'block';
                searchErrorMsg.innerText = '';
            } else {
                searchErrorMsg.innerText = `"${searchNicknameInput.value}" não encontrado.`;
                searchResultArea.style.display = 'none';
            }
            break;

        case 'ADD_FRIEND_RESPONSE':
            searchErrorMsg.innerText = payload.message;
            if (payload.success) {
                setTimeout(() => {
                    hideDialog(addContactDialog);
                    resetAddContactDialog();
                }, 1000);
            }
            break;


        case 'INCOMING_FRIEND_REQUEST':
            processFriendRequest(payload.from_nickname);
            break;

        case 'FRIEND_REQUEST_ACCEPTED':
            const { by_nickname, status } = payload;
            console.log(`Agora você é amigo de ${by_nickname}`);
            state.contacts.set(by_nickname, { nickname: by_nickname, status: status });
            renderContacts();
            break;

        case 'PENDING_FRIEND_REQUESTS':
            const requesters = payload.requests_from;
            if (requesters && requesters.length > 0) {
                console.log(`Recebendo ${requesters.length} pedidos pendentes.`);

                const processQueue = async () => {
                    for (const from_nickname of requesters) {
                        D: processFriendRequest(from_nickname);
                    }
                };

                processQueue();
                section
            }
            break;

        case 'INCOMING_CALL':
            if (state.currentCall.status === 'idle') {
                state.currentCall.nickname = payload.from_nickname;
                state.currentCall.status = 'incoming';
                callerIdLabel.innerText = `${payload.from_nickname} está a ligar...`;
                showDialog(incomingCallDialog);
                ringtoneSound.play();
            }
            break;

        case 'CALL_ACCEPTED':
            if (state.currentCall.status === 'outgoing' || state.currentCall.status === 'incoming') {
                console.log("Servidor aceitou a chamada, iniciando motor C++...");
                startVoipSession(payload);
            }
            break;

        case 'CALL_REJECTED':
            if (state.currentCall.status === 'outgoing') {
                console.log(`Chamada rejeitada por ${payload.callee_nickname}`);
                endCurrentCall();
            }
            break;

        case 'CALL_ENDED':
            if (state.currentCall.status !== 'idle') {
                console.log(`Chamada encerrada por ${payload.from_nickname}`);
                endCurrentCall();
            }
            break;
    }
});

// Inicialização
renderContacts();
window.electron.send('to-server', {
    command: 'GET_INITIAL_DATA',
    payload: {}
});