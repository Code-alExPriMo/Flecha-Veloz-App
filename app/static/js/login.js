document.getElementById('togglePassword').addEventListener('click', function (e) {
    const passwordInput = document.getElementById('password');
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
});
document.getElementById("loginForm").addEventListener("submit", async function(event) {
    // 1. Detenemos la recarga automática de la página
    event.preventDefault(); 

    // 2. Capturamos los datos que escribió el usuario
    const dni = document.getElementById("dni").value;
    const password = document.getElementById("password").value;
    const mensajeError = document.getElementById("mensaje-error");

    try {
        // 3. Tocamos la puerta de nuestro backend en Python
        const response = await fetch("/api/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ dni, password })
        });

        const data = await response.json();

        // 4. Evaluamos la respuesta de FastAPI
        if (response.ok) {
            // Guardamos TODOS los datos críticos en la bóveda del navegador
            localStorage.setItem("id_usuario", data.id_usuario); // <- ¡ESTO FALTABA!
            localStorage.setItem("id_rol", data.id_rol);         // <- Para separar vistas
            localStorage.setItem("usuarioNombre", data.nombre);
            localStorage.setItem("usuarioCorreo", data.correo);
            
            let rolTexto = "Chofer";
            if (data.id_rol === 1) rolTexto = "Gerente Principal";
            if (data.id_rol === 2) rolTexto = "Administrativo";
            localStorage.setItem("usuarioRol", rolTexto);
            
            mensajeError.style.color = "#4CAF50";
            mensajeError.textContent = "Acceso concedido. Entrando al sistema...";
            
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 1000);
        } else {
            mensajeError.style.color = "#f44336"; // Rojo
            mensajeError.textContent = data.detail || "Error al iniciar sesión.";
        }
    } catch (error) {
        mensajeError.style.color = "#f44336";
        mensajeError.textContent = "Error de conexión con el servidor.";
    }
});