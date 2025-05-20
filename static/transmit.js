const socket = io();
const video = document.getElementById('localVideo');
const canvas = document.createElement('canvas');
const ctx = canvas.getContext('2d');

let selectedDeviceId = null;
let detectCover = false;
let pingTimer = null;

socket.on("connect", () => {
    if (!pingTimer) {
        pingTimer = setInterval(() => {
            socket.emit("camera_ping", { camera_id: CAMERA_ID });
        }, 10_000);
    }
});
window.addEventListener("beforeunload", () => {
    clearInterval(pingTimer);
    socket.disconnect();
});

fetch("/api/cover_detection", {
        credentials: "include"
    })
    .then(r => r.json())
    .then(data => {
        detectCover = data.enabled;
        startVideo();
    });
async function startVideo() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === "videoinput");

    selectedDeviceId = videoDevices.find(d => d.deviceId === DEVICE_ID)?.deviceId;

    if (!selectedDeviceId) {
        alert("Камера с указанным deviceId не найдена.");
        return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
        video: {
            deviceId: {
                exact: selectedDeviceId
            }
        }
    });

    video.srcObject = stream;
    video.play();
    socket.emit('camera_settings', {
        detect_cover: detectCover
    });
    video.onloadedmetadata = () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

    setInterval(() => {
        socket.emit("camera_ping", { camera_id: CAMERA_ID });
    }, 10000);

        setInterval(() => {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const dataURL = canvas.toDataURL('image/jpeg');
            socket.emit('frame', {
                image: dataURL,
                camera_id: CAMERA_ID
            });
        }, 600);
    };
}
