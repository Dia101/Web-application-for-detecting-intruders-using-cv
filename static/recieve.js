const socket = io();

const img = document.getElementById('resultImage');
socket.on('processed_frame', data => {
    console.log("Получен кадр:", data.slice(0, 30));
    if (data && data.startsWith('data:image')) {
        img.src = data;
    } else {
        console.warn("Получены нестандартные данные:", data);
    }
});
