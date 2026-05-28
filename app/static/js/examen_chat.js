// examen_chat.js
// Lógica combinada para manejo de CRUD de exámenes y chat en tiempo real
// Depende de que la plantilla defina `window.INIT_DATA` antes de cargar este script.

(() => {
    const cfg = window.INIT_DATA || {};
    const currentUserId = cfg.currentUserId || null;
    const currentUserName = cfg.currentUserName || '';
    const isTecnico = !!cfg.isTecnico;

    // Helper: mostrar alertas (usa la misma UI que las plantillas)
    function mostrarAlerta(message, type='info') {
        const container = document.getElementById('alertContainer') || document.createElement('div');
        const div = document.createElement('div');
        div.className = `alert alert-${type === 'danger' ? 'danger' : (type === 'success' ? 'success' : 'info')}`;
        div.style.padding = '12px 16px'; div.style.borderRadius = '12px'; div.style.marginBottom = '8px';
        div.textContent = message;
        container.appendChild(div);
        setTimeout(() => div.remove(), 5000);
    }

    // ── EXÁMENES (CRUD via fetch) ─────────────────────
    let examenEditandoId = null;

    document.addEventListener('DOMContentLoaded', cargarExamenes);

    document.getElementById('btnCrearExamen')?.addEventListener('click', async () => {
        examenEditandoId = null;
        document.getElementById('modalTitle').textContent = 'Nuevo Examen';
        document.getElementById('examenForm').reset();
        if (isTecnico) await cargarPacientes();
        document.getElementById('examenModal').classList.add('open');
    });

    async function cargarPacientes() {
        try {
            const res = await fetch('/pacientes');
            const data = await res.json();
            const select = document.getElementById('selectPaciente');
            if (!select) return;
            select.innerHTML = '<option value="">-- Selecciona un paciente --</option>';
            if (data.success && data.pacientes.length) {
                data.pacientes.forEach(p => {
                    const opt = document.createElement('option'); opt.value = p.id; opt.textContent = `${p.nombre} (${p.cedula})`;
                    select.appendChild(opt);
                });
            }
        } catch (e) { mostrarAlerta('Error cargando pacientes: '+e.message,'danger'); }
    }

    document.getElementById('examenForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = document.getElementById('examenForm');
        const formData = new FormData(form);
        const datos = Object.fromEntries(formData.entries());
        try {
            let url = '/examenes'; let metodo = 'POST';
            if (examenEditandoId) { url = `/examenes/${examenEditandoId}`; metodo = 'PUT'; }
            const res = await fetch(url, {
                method: metodo,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos)
            });
            const resultado = await res.json();
            if (resultado.success) { mostrarAlerta(resultado.mensaje,'success'); cerrarModal(); cargarExamenes(); }
            else mostrarAlerta(resultado.error || 'Error desconocido','danger');
        } catch (err) { mostrarAlerta('Error al guardar examen: '+err.message,'danger'); }
    });

    async function cargarExamenes() {
        const container = document.getElementById('examenesContainer');
        if (!container) return;
        container.innerHTML = '<div class="loading"><i class="bi bi-hourglass-split"></i> Cargando exámenes...</div>';
        try {
            const res = await fetch('/examenes');
            const data = await res.json();
            if (!data.success) { container.innerHTML = '<div class="empty-state">No hay exámenes.</div>'; return; }
            const examenes = data.examenes || [];
            // Render simple table (the template's CSS will style it)
            let html = '<div class="table-wrap"><table><thead><tr>';
            if (isTecnico) html += '<th>Paciente</th>';
            html += '<th>Nombre</th><th>Descripción</th><th>Precio</th><th>Tiempo entrega</th>';
            if (isTecnico) html += '<th style="text-align:center">Acciones</th>';
            html += '</tr></thead><tbody>';
            if (examenes.length === 0) html += '<tr class="empty-row"><td colspan="6">No hay exámenes disponibles</td></tr>';
            examenes.forEach(ex => {
                html += '<tr>';
                if (isTecnico) html += `<td><strong>${ex.usuario_nombre}</strong></td>`;
                html += `<td><strong>${ex.nombre}</strong></td><td>${ex.descripcion}</td><td>$${parseFloat(ex.precio).toFixed(2)}</td><td>${ex.tiempo_entrega}</td>`;
                if (isTecnico) html += `<td style="text-align:center"><div class="action-buttons"><button class="btn-edit" onclick="window.abrirExamenEditor(${ex.id})">Editar</button><button class="btn-delete" onclick="window.confirmarEliminar(${ex.id}, '${ex.nombre.replace(/'/g,"\\'") }')">Eliminar</button></div></td>`;
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            container.innerHTML = html;
        } catch (e) { container.innerHTML = '<div class="empty-state">Error cargando exámenes</div>'; console.error(e); }
    }

    window.abrirExamenEditor = async function(id) {
        examenEditandoId = id;
        document.getElementById('modalTitle').textContent = 'Editar Examen';
        const res = await fetch(`/examenes/${id}`);
        const data = await res.json();
        if (data.success) {
            const ex = data.examen;
            document.getElementById('inputNombre').value = ex.nombre || '';
            document.getElementById('inputDesc').value = ex.descripcion || '';
            document.getElementById('inputPrecio').value = ex.precio || '';
            document.getElementById('inputTiempo').value = ex.tiempo_entrega || '';
            if (isTecnico) { await cargarPacientes(); document.getElementById('selectPaciente').value = ex.usuario_id || ''; }
            document.getElementById('examenModal').classList.add('open');
        } else mostrarAlerta(data.error || 'No se pudo cargar examen','danger');
    };

    window.confirmarEliminar = function(id,nombre){
        const deleteBackdrop = document.getElementById('deleteBackdrop');
        if (!deleteBackdrop) return;
        document.getElementById('deleteNombre').textContent = nombre;
        const form = document.getElementById('deleteForm');
        if (form) form.action = `/examenes/${id}`; // server expects DELETE on this endpoint
        deleteBackdrop.classList.add('open');
    };

    // Enviar DELETE por fetch cuando se haga submit en deleteForm
    document.getElementById('deleteForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const action = e.target.action;
        try {
            const res = await fetch(action, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) { mostrarAlerta(data.mensaje,'success'); cerrarDelete(); cargarExamenes(); }
            else mostrarAlerta(data.error||'Error eliminando','danger');
        } catch (err) { mostrarAlerta('Error eliminando: '+err.message,'danger'); }
    });

    function cerrarModal(){ document.getElementById('examenModal')?.classList.remove('open'); }
    function cerrarDelete(){ document.getElementById('deleteBackdrop')?.classList.remove('open'); }

    // ── BUSQUEDA EN TABLA SIMPLE ─────────────────────
    const searchInput = document.getElementById('searchExamen');
    if (searchInput) searchInput.addEventListener('input', () => {
        const q = searchInput.value.toLowerCase().trim();
        document.querySelectorAll('#tablaBody tr[data-nombre]').forEach(row => row.style.display = row.dataset.nombre.includes(q) ? '' : 'none');
    });

    // ── CHAT & WEBSOCKETS ───────────────────────────
    // depende de socket.io cargado globalmente
    if (typeof io !== 'undefined') {
        const socket = io();
        let currentChatPacienteId = isTecnico ? null : currentUserId;

        socket.on('connect', () => {
            console.log('WS connected');
            if (currentChatPacienteId) { socket.emit('join',{paciente_id: currentChatPacienteId}); cargarHistorialChat(currentChatPacienteId); }
        });

        socket.on('notificacion', (data) => mostrarAlerta(data.mensaje, data.tipo || 'info'));

        socket.on('receive_message', (msg) => { if (msg.remitente_id === currentUserId) return; renderizarMensaje(msg); });

        function renderizarMensaje(msg, esMio){
            const chatMessages = document.getElementById('chatMessages'); if (!chatMessages) return;
            const esMioReal = (msg.remitente_id === currentUserId) || !!esMio;
            if (chatMessages.querySelector('.bi-chat-quote')) chatMessages.innerHTML = '';
            const div = document.createElement('div'); div.style.maxWidth='70%'; div.style.padding='10px 14px'; div.style.borderRadius='12px'; div.style.fontSize='14px'; div.style.lineHeight='1.4'; div.style.wordBreak='break-word';
            if (esMioReal) { div.style.alignSelf='flex-end'; div.style.background='rgba(59,130,246,0.8)'; div.style.color='white'; div.style.borderBottomRightRadius='4px'; }
            else { div.style.alignSelf='flex-start'; div.style.background='rgba(255,255,255,0.1)'; div.style.color='var(--text-primary)'; div.style.borderBottomLeftRadius='4px'; const senderName=document.createElement('div'); senderName.style.fontSize='11px'; senderName.style.color='#9ca3af'; senderName.style.marginBottom='4px'; senderName.textContent = msg.rol === 'Tecnico' ? 'Laboratorio' : msg.remitente_nombre; div.appendChild(senderName); }
            div.appendChild(document.createTextNode(msg.contenido)); chatMessages.appendChild(div); chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        async function cargarHistorialChat(pacienteId){
            try{
                const res = await fetch(`/mensajes/${pacienteId}`); const data = await res.json(); const chatMessages = document.getElementById('chatMessages'); if(!chatMessages) return; chatMessages.innerHTML='';
                if (data.success && data.mensajes.length) data.mensajes.forEach(m=>renderizarMensaje(m)); else chatMessages.innerHTML = `<div style="text-align:center;color:var(--text-secondary);margin-top:auto;margin-bottom:auto;"><i class="bi bi-chat-quote" style="font-size:32px;display:block;margin-bottom:12px;opacity:.5"></i>No hay mensajes aún</div>`;
            }catch(e){ console.error('Error historial', e); }
        }

        function enviarMensaje(){ const input=document.getElementById('chatInput'); const texto=input?.value.trim(); if(!texto || !currentChatPacienteId) return; const msgObj={ paciente_id: currentChatPacienteId, contenido: texto, remitente_id: currentUserId, remitente_nombre: currentUserName, rol: cfg.role || '' }; socket.emit('send_message', msgObj); renderizarMensaje(msgObj, true); input.value=''; }

        document.getElementById('chatSendBtn')?.addEventListener('click', enviarMensaje);
        document.getElementById('chatInput')?.addEventListener('keypress', e => { if (e.key === 'Enter') enviarMensaje(); });

        if (isTecnico) {
            fetch('/pacientes').then(r=>r.json()).then(data=>{
                if(data.success){ const list=document.getElementById('chatPacientesList'); if(!list) return; list.innerHTML=''; data.pacientes.forEach(p=>{
                    const btn=document.createElement('div'); btn.style.padding='12px'; btn.style.borderBottom='1px solid rgba(255,255,255,0.05)'; btn.style.cursor='pointer'; btn.style.transition='background 0.2s'; btn.textContent=p.nombre; btn.onmouseover=()=>btn.style.background='rgba(255,255,255,0.05)'; btn.onmouseout=()=>btn.style.background='transparent'; btn.onclick=()=>{ if(currentChatPacienteId) socket.emit('leave',{paciente_id:currentChatPacienteId}); currentChatPacienteId=p.id; socket.emit('join',{paciente_id:p.id}); document.getElementById('chatHeader').textContent = `Chat con: ${p.nombre}`; document.getElementById('chatInput').disabled=false; document.getElementById('chatSendBtn').disabled=false; cargarHistorialChat(p.id); }; list.appendChild(btn);
                }); }
            }).catch(()=>{});
        }
    }

    // Exponer cierre y apertura de modales globalmente si la plantilla los invoca
    window.cerrarModal = cerrarModal; window.cerrarDelete = cerrarDelete;
})();
