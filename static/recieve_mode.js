function checkAndOpenCamera(cameraId) {
    fetch(`/api/is_camera_active?camera_id=${cameraId}`, {
        credentials: "include"
    })
    .then(r => r.json())
    .then(data => {
        if (data.active) {
            window.location.href = `/recieve?camera_id=${cameraId}`;
        } else {
            alert("Камера неактивна. Запустите трансляцию.");
        }
    })
    .catch(() => {
        alert("Ошибка при проверке активности камеры.");
    });
}
