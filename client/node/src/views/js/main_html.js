// --- Elementos do DOM e Áudio ---
const contactList = document.getElementById('contact-list');
const loggedInUserNickname = document.getElementById('user-nickname');
const addContactBtn = document.getElementById('add-contact-btn');
const logoutBtn = document.getElementById('logout-btn');
const ringtoneSound = document.getElementById('ringtone-sound');
const dialingSound = document.getElementById('dialing-sound');
const hangupSound = document.getElementById('hangup-sound');
const incomingCallDialog = document.getElementById('incoming-call-dialog');
const callerIdLabel = document.getElementById('caller-id-label');
const acceptCallBtn = document.getElementById('accept-call-btn');
const refuseCallBtn = document.getElementById('refuse-call-btn');
const addContactDialog = document.getElementById('add-contact-dialog');
const searchNicknameInput = document.getElementById('search-nickname-input');
const searchContactBtn = document.getElementById('search-contact-btn');
const searchResultArea = document.getElementById('search-result-area');
const foundContactNickname = document.getElementById('found-contact-nickname');
const sendRequestBtn = document.getElementById('send-request-btn');
const searchErrorMsg = document.getElementById('search-error-msg');
const callWindowDialog = document.getElementById('call-window-dialog');
const outgoingCallState = document.getElementById('outgoing-call-state');
const outgoingCallLabel = document.getElementById('outgoing-call-label');
const cancelCallBtn = document.getElementById('cancel-call-btn');
const activeCallState = document.getElementById('active-call-state');
const activeCallLabel = document.getElementById('active-call-label');
const endCallBtn = document.getElementById('end-call-btn');

// --- Estado da Aplicação ---
const state = {
    currentUser: localStorage.getItem('currentUserNickname') || 'user_error',
    sessionToken: localStorage.getItem('sessionToken') || null,
    contacts: new Map(),
    currentCall: {
        nickname: null,
        status: 'idle'
    }
};
loggedInUserNickname.innerText = state.currentUser;

if (!state.sessionToken) {
    alert("Token de sessão não encontrado. Faça o login novamente.");
}

// --- Funções de UI ---
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

// --- Funções Principais ---

async function searchContact() {
    const nicknameToSearch = searchNicknameInput.value;
    searchErrorMsg.innerText = '';
    searchResultArea.style.display = 'none';
    if (!nicknameToSearch) {
        searchErrorMsg.innerText = 'Por favor, digite um nickname.';
        return;
    }

    try {
        const results = await window.api.callRMI('search_users', [state.sessionToken, nicknameToSearch]);
        
        if (results && results.length > 0) {
            const foundUser = results[0];
            foundContactNickname.innerText = foundUser.nickname;
            searchResultArea.style.display = 'block';
            searchErrorMsg.innerText = '';
        } else {
            searchErrorMsg.innerText = `"${nicknameToSearch}" não encontrado.`;
            searchResultArea.style.display = 'none';
        }
    } catch (e) {
        searchErrorMsg.innerText = e.message;
    }
}

async function initiateCall(calleeNickname) {
    console.log(`Iniciando chamada para ${calleeNickname}`);
    state.currentCall.nickname = calleeNickname;
    state.currentCall.status = 'outgoing';

    outgoingCallLabel.innerText = `A ligar para ${calleeNickname}...`;
    outgoingCallState.style.display = 'block';
    activeCallState.style.display = 'none';
    showDialog(callWindowDialog);

    dialingSound.play();

    try {
        const [success, message] = await window.api.callRMI('invite_to_call', [state.sessionToken, calleeNickname]);
        if (!success) {
            alert(message);
            endCurrentCall();
        }
    } catch (e) {
        alert(e.message);
        endCurrentCall();
    }
}

// --- Lógica do C++  ---
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
        
        my_user_info_json: JSON.stringify({ userId: state.currentUser })
    };

    const result = window.voip.startCall(voipOptions, onVoipEvent);

    if (result.success) {
        console.log("Motor VoIP C++ iniciado com sucesso!");
        state.currentCall.status = 'active';

        stopAllCallSounds();

        const partnerNickname = (state.currentUser === callData.callee_nickname) 
                                ? state.currentCall.nickname 
                                : callData.callee_nickname;

        activeCallLabel.innerText = `Em chamada com ${partnerNickname}`;
        outgoingCallState.style.display = 'none';
        activeCallState.style.display = 'block';
        showDialog(callWindowDialog);

    } else {
        console.error("FALHA ao iniciar o motor VoIP C++:", result.error);
        alert(`Erro ao iniciar áudio: ${result.error}`);
    }
}

// --- Event Listeners  ---
addContactBtn.addEventListener('click', () => showDialog(addContactDialog));

logoutBtn.addEventListener('click', () => {
    console.log("Enviando pedido 'quit-app' para o main.js");
    window.api.send('quit-app'); 
});

acceptCallBtn.addEventListener('click', async () => {
    console.log("Botão 'Aceitar' clicado.");
    stopAllCallSounds();
    hideDialog(incomingCallDialog);

    try {
        const relayInfo = await window.api.callRMI('accept_call', [state.sessionToken, state.currentCall.nickname]);
        
        if (relayInfo && relayInfo.relay_ip) {
            console.log("Servidor aceitou a chamada, iniciando motor C++...");
            startVoipSession(relayInfo);
        } else {
            throw new Error("Servidor retornou dados de relay inválidos.");
        }
    } catch (e) {
        alert(`Erro ao aceitar chamada: ${e.message}`);
        endCurrentCall();
    }
});

refuseCallBtn.addEventListener('click', async () => {
    console.log("Botão 'Recusar' clicado.");
    try {
        await window.api.callRMI('reject_call', [state.sessionToken, state.currentCall.nickname]);
    } catch (e) {
        console.warn("Erro ao rejeitar chamada:", e.message);
    }
    endCurrentCall();
});

searchContactBtn.addEventListener('click', searchContact);

sendRequestBtn.addEventListener('click', async () => {
    const targetNickname = foundContactNickname.innerText;
    if (!targetNickname) return;
    
    try {
        const [success, message] = await window.api.callRMI('send_friend_request', [state.sessionToken, targetNickname]);
        
        searchErrorMsg.innerText = message;
        if (success) { 
            setTimeout(() => {
                hideDialog(addContactDialog);
                resetAddContactDialog();
            }, 1000);
        }
    } catch (e) {
        searchErrorMsg.innerText = e.message;
    }
});

addContactDialog.addEventListener('click', (e) => {
    if (e.target === addContactDialog) {
        hideDialog(addContactDialog);
        resetAddContactDialog();
    }
});

// Botões de chamada (cancelar/encerrar)
async function handleEndCallClick() {
    console.log("Botão 'Encerrar' ou 'Cancelar' clicado.");
    try {
        await window.api.callRMI('end_call', [state.sessionToken]);
    } catch (e) {
        console.warn("Erro ao enviar 'end_call' ao servidor:", e.message);
    }
    endCurrentCall(); 
}
cancelCallBtn.addEventListener('click', handleEndCallClick);
endCallBtn.addEventListener('click', handleEndCallClick);

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

// --- Lógica de Polling  ---
async function processServerEvent(event) {
    console.log("Processando evento do Polling:", event);
    const command = event.command;
    const payload = event;

    const processFriendRequest = async (from_nickname) => {
        const accepted = confirm(`${from_nickname} quer te adicionar como amigo. Aceitar?`);
        
        const method = accepted ? 'accept_friend_request' : 'reject_friend_request';
        try {
            await window.api.callRMI(method, [state.sessionToken, from_nickname]);
            if (accepted) loadInitialData(); 
        } catch(e) {
            alert(`Erro ao responder pedido de ${from_nickname}: ${e.message}`);
        }
    };

    switch (command) {
        case 'STATUS_UPDATE':
            if (state.contacts.has(payload.nickname)) {
                state.contacts.get(payload.nickname).status = payload.status;
                renderContacts();
            }
            break;
        case 'INCOMING_FRIEND_REQUEST':
            await processFriendRequest(payload.from_nickname);
            break;
        case 'FRIEND_REQUEST_ACCEPTED':
            const { by_nickname, status } = payload;
            console.log(`Agora você é amigo de ${by_nickname}`);
            state.contacts.set(by_nickname, { nickname: by_nickname, status: status });
            renderContacts();
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
            if (state.currentCall.status === 'outgoing' && state.currentCall.nickname === payload.callee_nickname) {
                 console.log("Servidor aceitou (eu sou o autor), iniciando motor C++...");
                 startVoipSession(payload);
            }
            break;
        case 'CALL_REJECTED':
            if (state.currentCall.status === 'outgoing' && state.currentCall.nickname === payload.callee_nickname) {
                console.log(`Chamada rejeitada por ${payload.callee_nickname}`);
                endCurrentCall();
            }
            break;
        case 'CALL_ENDED':
            if (state.currentCall.status !== 'idle' && state.currentCall.nickname === payload.from_nickname) {
                console.log(`Chamada encerrada por ${payload.from_nickname}`);
                endCurrentCall();
            }
            break;
    }
}

async function pollForUpdates() {
    if (!state.sessionToken) return;

    try {
        const events = await window.api.callRMI('get_updates', [state.sessionToken]);
        
        if (events && events.length > 0) {
            for (const event of events) {
                await processServerEvent(event);
            }
        }
    } catch (error) {
        console.error("Erro no polling:", error.message);
        if (error.message.includes("Token de sessão inválido")) {
             clearInterval(pollingInterval);
             alert("Sua sessão expirou. Faça o login novamente.");
             window.api.send('quit-app'); 
        }
    }
}

// --- Inicialização da Aplicação ---
async function loadInitialData() {
    if (!state.sessionToken) return;
    try {
        const data = await window.api.callRMI('get_initial_data', [state.sessionToken]);
        
        state.contacts.clear();
        if (data.friends) {
            for (const friend of data.friends) {
                state.contacts.set(friend.nickname, friend);
            }
        }
        renderContacts();

        if (data.pending && data.pending.length > 0) {
            console.log(`Recebendo ${data.pending.length} pedidos pendentes.`);
            for (const from_nickname of data.pending) {
                await processServerEvent({ 
                    command: 'INCOMING_FRIEND_REQUEST', 
                    from_nickname: from_nickname 
                });
            }
        }
    } catch (e) {
        console.error("Erro ao carregar dados iniciais:", e.message);
    }
}

// Inicialização
loadInitialData();
const pollingInterval = setInterval(pollForUpdates, 2000);