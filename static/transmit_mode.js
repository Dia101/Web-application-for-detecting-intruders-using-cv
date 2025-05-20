const socket = io();

function getCSRFTokenFromCookie() {
    const match = document.cookie.match(/csrf_access_token=([^;]+)/);
    return match ? match[1] : null;
}

document.addEventListener("DOMContentLoaded", async() => {
    const select = document.getElementById("deviceSelect");
    try {
        const toggle = document.getElementById('detectCoverToggle');
        console.log("Чекбокс найден:", toggle);
        if (toggle) {
            toggle.addEventListener('change', () => {
                socket.emit('camera_settings', {
                    detect_cover: toggle.checked
                });
                console.log("Отправлен camera_settings:", toggle.checked);
            });
        }
        await navigator.mediaDevices.getUserMedia({
            video: true
        });
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => {
            const name = (d.label || "").toLowerCase();
            return !name.includes("virtual") && !name.includes("obs");
        });

        videoDevices
            .filter(device => device.label)
            .forEach((device, index) => {
                const option = document.createElement("option");
                option.value = device.deviceId;
                option.text = device.label || `Камера ${index + 1}`;
                select.appendChild(option);
            });
    } catch (err) {
        console.error("Ошибка доступа к камере:", err);
        alert("Разрешите доступ к камере для отображения списка устройств.");
    }
});

document.getElementById("add-camera-form").addEventListener("submit", async(e) => {
    e.preventDefault();
    const name = e.target.camera_name.value;
    const deviceId = document.getElementById("deviceSelect").value;

    const res = await fetch("/api/add_camera", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRF-TOKEN": getCSRFTokenFromCookie()
        },
        credentials: "include",
        body: JSON.stringify({
            name, device_id: deviceId
        })
    });

    if (res.ok) {
        e.target.reset();
        location.reload();
    } else {
        alert("Ошибка при добавлении камеры");
    }
});

async function deleteCamera(cameraId) {
    if (!confirm("Удалить камеру?")) return;

    const res = await fetch(`/api/delete_camera/${cameraId}`, {
        method: "DELETE",
        headers: {
            "X-CSRF-TOKEN": getCSRFTokenFromCookie()
        },
        credentials: "include"
    });

    if (res.ok) {
        const li = document.getElementById(`cam-${cameraId}`);
        if (li) li.remove();
    } else {
        alert("Ошибка при удалении камеры");
    }
}

socket.on('connect', () => {
    socket.emit('join_user_room');
});

socket.on('update_cover_toggle', data => {
    const toggle = document.getElementById('detectCoverToggle');
    if (toggle) toggle.checked = data.detect_cover;
});
