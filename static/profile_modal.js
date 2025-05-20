function getCSRFTokenFromCookie() {
    const match = document.cookie.match(/csrf_access_token=([^;]+)/);
    console.log("csrf из cookie:", match ? match[1] : "не найден");
    return match ? match[1] : null;
}

//Открытие модельного окна
function openProfileModal(username) {
    document.getElementById("modal-username").innerText = username;
    const modal = document.getElementById("profileModal");
    modal.style.display = "flex";
    fetchTelegramChats();
}

// Отображение имени пользователя в модальном окне
async function profileModalUsername() {
    try {
        const res = await fetch("/api/get_user_name", {
            credentials: "include"
        });
        const data = await res.json();
        const name = data.name || "Без имени";
        openProfileModal(name);
    } catch (err) {
        console.error("Ошибка загрузки имени пользователя:", err);
        openProfileModal("Неизвестно");
    }
}

// Закрытик модального окна
function closeModal() {
    const modal = document.getElementById("profileModal");
    modal.style.display = "none";
    document.getElementById("code-section").classList.add("hidden");
    document.getElementById("generate-section").classList.remove("hidden");
}

//Отображение привязанных аккаунтов Телеграмм
function fetchTelegramChats() {
    fetch("/api/get_telegram_chats")
        .then(res => {
            if (!res.ok) {
                if (res.status === 401) {
                    window.location.href = "/login";
                    return Promise.reject();
                }
                throw new Error(`Ошибка ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            const list = document.getElementById("telegram-list");
            list.innerHTML = "";
            data.forEach(acc => {
                const li = document.createElement("li");
                li.innerHTML = `@${acc.telegram_username || 'неизвестно'} <button class="remove-button" onclick="deleteTelegram(${acc.id})">✖</button>`;
                list.appendChild(li);
            });
        })
        .catch(err => {
            if (err) {
                console.error(err);
                alert("Не удалось получить список аккаунтов");
            }
        });
}

//Генерация кода для Телеграм
function generateTelegramCode() {
    // generate_telegram_code генерирует число, преобразует его в строку и сохраняет в базе данных
    fetch("/api/generate_telegram_code", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-TOKEN": getCSRFTokenFromCookie()
            },
            credentials: "include"
        })
        .then(res => {
            if (!res.ok) {
                if (res.status === 401) {
                    window.location.href = "/login";
                    return Promise.reject();
                }
                throw new Error(`Ошибка ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("Сгенерирован код:", data.code);
            showCodePopup(data.code);
        })
        .catch(err => {
            if (err) {
                console.error(err);
                alert("Ошибка при генерации кода");
            }
        });
}
//Удаление Телеграм-аккаунта из списка
function deleteTelegram(id) {
    fetch(`/api/delete_telegram_chat/${id}`, {
            method: "DELETE",
            headers: {
                "X-CSRF-TOKEN": getCSRFTokenFromCookie()
            },
            credentials: "include"
        })
        .then(res => {
            if (!res.ok) {
                if (res.status === 401) {
                    window.location.href = "/login";
                    return Promise.reject();
                }
                throw new Error(`Ошибка ${res.status}`);
            }
            fetchTelegramChats();
        })
        .catch(err => {
            if (err) {
                console.error(err);
                alert("Не удалось удалить чат");
            }
        });
}

//Отображение кода
function showCodePopup(code) {
    document.getElementById("code-popup-value").innerText = code;
    document.getElementById("codePopupModal").style.display = "flex";
}

//Закрытие окна с кодом
function closeCodePopup() {
    document.getElementById("codePopupModal").style.display = "none";
}

//Кнопка копирования кода
function copyCode() {
    const code = document.getElementById("code-popup-value").innerText;
    navigator.clipboard.writeText(code).then(() => {
        alert("Код скопирован в буфер обмена!");
    });
}
