const translations = {
    en: {
        createPoll: "Create a Poll",
        pollTitle: "Poll Title",
        options: "Options",
        addOption: "Add Option",
        deleteOption: "Delete",
        password: "Password (6 digits)",
        endDate: "End Date (up to 15 days)",
        submit: "Create Poll",
        optionPlaceholder: ["Option 1", "Option 2", "New Option"],
        toastCreateLink: "Poll link created successfully.",
        toastCopyLink: "Link copied to clipboard.",
        toastCopyText: "Text copied to clipboard.",
        maxOptionsError: "You can add up to 10 options.",
        titleError: "Please provide a title for the poll.",
        optionError: "Please provide at least two options for the poll.",
        dateError: "End date must be within 15 days from today.",
        footerMessage: `This poll page does not store any personal information other than the poll title, content, date, and vote count.
        A unique ID is assigned based on the user's device settings, but it does not identify the user.
        It does not fully guarantee one person, one vote.`,
        iframeInstructions: "Paste the code below into the HTML tab of the board.",
        createLinkInstructions: "Poll link created successfully."
    },
    ko: {
        createPoll: "투표 생성",
        pollTitle: "투표 제목",
        options: "옵션",
        addOption: "옵션 추가",
        deleteOption: "삭제",
        password: "비밀번호 (6자리)",
        endDate: "종료 날짜 (최대 15일)",
        submit: "투표 생성",
        optionPlaceholder: ["옵션 1", "옵션 2", "새 옵션"],
        toastCreateLink: "투표링크가 생성되었습니다.",
        toastCopyLink: "링크가 클립보드에 복사되었습니다.",
        toastCopyText: "텍스트가 클립보드에 복사되었습니다.",
        maxOptionsError: "옵션은 최대 10개까지만 추가할 수 있습니다.",
        titleError: "투표 제목을 입력하세요.",
        optionError: "최소 두 개의 옵션을 입력하세요.",
        dateError: "종료 날짜는 오늘부터 최대 15일 이내여야 합니다.",
        footerMessage: `해당 투표 페이지는 투표 제목, 내용, 날짜 및 투표 수 외에 어떠한 개인 정보도 저장하지 않습니다.
        투표 시 사용자 기기의 설정을 조합하여 고유한 ID가 부여되지만, 이를 통해 사용자를 특정할 수는 없습니다.
        1인 1표를 완벽하게 보장하지는 않습니다.`,
        iframeInstructions: "아래 코드를 게시판의 HTML 탭에 붙여넣으세요.",
        createLinkInstructions: "투표링크가 생성되었습니다."
    }
};

function setLanguage(lang) {
    const elements = translations[lang];
    document.getElementById('create-poll-title').textContent = elements.createPoll;
    document.getElementById('poll-title-label').textContent = elements.pollTitle;
    document.getElementById('options-label').textContent = elements.options;
    document.getElementById('add-option-btn').textContent = elements.addOption;
    document.getElementById('password-label').textContent = elements.password;
    document.getElementById('end-date-label').textContent = elements.endDate;
    document.querySelector('button[type="submit"]').textContent = elements.submit;
    document.getElementById('footer-message').textContent = elements.footerMessage;
    document.getElementById('iframe-instructions').textContent = elements.iframeInstructions;

    const createLinkInstructions = document.getElementById('create-link-instructions');
    if (createLinkInstructions) {
        createLinkInstructions.textContent = elements.createLinkInstructions;
    }

    // 옵션 Placeholder 업데이트
    const placeholders = elements.optionPlaceholder;
    const options = document.querySelectorAll('input[name="options[]"]');
    options.forEach((input, index) => {
        input.placeholder = placeholders[index] || placeholders[2];
    });

    // 옵션 삭제 버튼 텍스트 업데이트
    document.querySelectorAll('.remove-option-btn').forEach(button => {
        button.textContent = elements.deleteOption;
    });

    updateLanguageButtonStyles(lang);
    localStorage.setItem('selectedLanguage', lang);
}

function updateLanguageButtonStyles(selectedLang) {
    const langEnButton = document.getElementById('lang-en');
    const langKoButton = document.getElementById('lang-ko');

    if (selectedLang === 'en') {
        langEnButton.classList.add('btn-selected');
        langEnButton.classList.remove('btn-outline-secondary');
        langKoButton.classList.remove('btn-selected');
        langKoButton.classList.add('btn-outline-secondary');
    } else {
        langKoButton.classList.add('btn-selected');
        langKoButton.classList.remove('btn-outline-secondary');
        langEnButton.classList.remove('btn-selected');
        langEnButton.classList.add('btn-outline-secondary');
    }
}

function loadLanguage() {
    const savedLanguage = localStorage.getItem('selectedLanguage') || 'ko';
    setLanguage(savedLanguage);
}

document.getElementById('lang-en').addEventListener('click', () => setLanguage('en'));
document.getElementById('lang-ko').addEventListener('click', () => setLanguage('ko'));

loadLanguage();

function setDefaultEndDate() {
    const endDateInput = document.getElementById('end_date');
    const currentDate = new Date();
    const minDate = new Date();
    const maxDate = new Date();

    // maxDate는 현재로부터 15일 뒤
    maxDate.setDate(currentDate.getDate() + 15);

    // endDateInput.value는 현재로부터 3일 뒤로 설정
    currentDate.setDate(currentDate.getDate() + 3);
    currentDate.setHours(23, 59, 59);

    const minDateFormatted = formatDateTime(minDate); // 최소 선택 가능한 날짜는 현재 시간
    const maxDateFormatted = formatDateTime(maxDate);
    const endDateFormatted = formatDateTime(currentDate); // 기본 종료 날짜는 3일 뒤

    endDateInput.value = endDateFormatted; // 종료 날짜 기본값을 3일 뒤로 설정
    endDateInput.min = minDateFormatted;   // 최소값은 현재 시간으로 설정
    endDateInput.max = maxDateFormatted;   // 최대값은 15일 뒤로 설정
}

function formatDateTime(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

window.onload = setDefaultEndDate;

document.getElementById('add-option-btn').addEventListener('click', function() {
    const optionsContainer = document.getElementById('options-container');
    const optionCount = optionsContainer.querySelectorAll('input[name="options[]"]').length;

    if (optionCount >= 10) {
        showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].maxOptionsError, 'danger');
        return;
    }

    const newOption = document.createElement('div');
    newOption.className = 'input-group mb-2';

    newOption.innerHTML = `
        <input type="text" class="form-control" name="options[]" placeholder="${translations[localStorage.getItem('selectedLanguage') || 'ko'].optionPlaceholder[2]}" required>
        <button type="button" class="btn btn-outline-danger btn-sm ms-2 remove-option-btn">${translations[localStorage.getItem('selectedLanguage') || 'ko'].deleteOption}</button>
    `;

    optionsContainer.appendChild(newOption);

    newOption.querySelector('.remove-option-btn').addEventListener('click', function() {
        optionsContainer.removeChild(newOption);
    });
});

document.getElementById('poll-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const title = document.getElementById('title').value.trim();
    const options = Array.from(document.querySelectorAll('input[name="options[]"]'))
        .map(option => option.value.trim())
        .filter(option => option !== '');
    const endDate = new Date(document.getElementById('end_date').value);
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 15);

    if (!title) {
        showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].titleError, 'danger');
        return;
    }

    if (options.length < 2) {
        showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].optionError, 'danger');
        return;
    }

    if (endDate <= new Date() || endDate > maxDate) {
        showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].dateError, 'danger');
        return;
    }

    const formData = new FormData(this);

    fetch('/create_poll', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayLink(data.message);
            displayIframeCode(data.message);
            showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].toastCreateLink);
        } else {
            showToast(data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while creating the poll.', 'danger');
    });
});

function displayLink(link) {
    const messageContainer = document.getElementById('message-container');
    messageContainer.innerHTML = `
        <span id="create-link-instructions">${translations[localStorage.getItem('selectedLanguage') || 'ko'].toastCreateLink}</span> 
        <button class="btn btn-outline-secondary btn-sm" id="copy-link-btn">Copy Link</button>
        <button class="btn btn-outline-primary btn-sm ms-2" id="go-to-link-btn">Go to Link</button>
        <input type="text" class="form-control mt-2" id="poll-link" value="${link}" readonly>
    `;
    messageContainer.style.display = 'block';

    document.getElementById('copy-link-btn').addEventListener('click', function() {
        navigator.clipboard.writeText(link).then(() => {
            showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].toastCopyLink);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            showToast('Failed to copy link.', 'danger');
        });
    });

    document.getElementById('go-to-link-btn').addEventListener('click', function() {
        window.open(link, '_blank'); 
    });
}

function displayIframeCode(link) {
    const iframeContainer = document.getElementById('iframe-container');
    const iframeCode = `<iframe src="${link}" width="600" height="800"></iframe>`;
    document.getElementById('iframe-code').value = iframeCode;
    iframeContainer.style.display = 'block';

    document.getElementById('copy-iframe-btn').addEventListener('click', function() {
        navigator.clipboard.writeText(iframeCode).then(() => {
            showToast(translations[localStorage.getItem('selectedLanguage') || 'ko'].toastCopyText);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            showToast('Failed to copy iframe code.', 'danger');
        });
    });
}

function showToast(message, type = 'success') {
    const toastElement = document.getElementById('copyToast');
    const toastMessageElement = document.getElementById('toast-message');
    toastMessageElement.innerHTML = message;
    toastElement.classList.remove('text-bg-success', 'text-bg-danger');
    toastElement.classList.add(`text-bg-${type}`);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}
