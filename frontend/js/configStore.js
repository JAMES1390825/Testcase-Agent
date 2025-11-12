const STORAGE_PREFIX = "tc_agent.";

const DEFAULTS = {
    apiKey: "",
    baseUrl: "",
    textModel: "",
    visionModel: "",
    disableVision: true,
    maxImagesPerBatch: "10",
    imageMaxSize: "1024",
    imageQuality: "85",
    maxSectionChars: "60000",
};

const state = { ...DEFAULTS };

function storageKey(key) {
    return `${STORAGE_PREFIX}${key}`;
}

function loadFromStorage() {
    Object.keys(DEFAULTS).forEach((key) => {
        const stored = window.localStorage.getItem(storageKey(key));
        if (stored === null) return;
        if (key === "disableVision") {
            state[key] = stored === "true";
        } else {
            state[key] = stored;
        }
    });
}

export function persistCurrentConfig() {
    Object.keys(DEFAULTS).forEach((key) => {
        const value = state[key];
        if (value === "" || value === undefined || value === null) {
            window.localStorage.removeItem(storageKey(key));
            return;
        }
        if (key === "disableVision") {
            window.localStorage.setItem(storageKey(key), value ? "true" : "false");
        } else {
            window.localStorage.setItem(storageKey(key), String(value));
        }
    });
}

function notifySubscribers() {
    const detail = getConfig();
    window.dispatchEvent(new CustomEvent("config:updated", { detail }));
}

export function initialiseConfigStore() {
    loadFromStorage();
    notifySubscribers();
}

export function getConfig() {
    return { ...state };
}

export function setConfigValue(key, value) {
    if (!(key in state)) {
        throw new Error(`Unknown config key: ${key}`);
    }

    if (key === "disableVision") {
        state[key] = Boolean(value);
    } else {
        state[key] = value ?? "";
    }

    notifySubscribers();
}

export function buildRequestConfig() {
    const config = getConfig();

    return {
        api_key: config.apiKey || undefined,
        base_url: config.baseUrl || undefined,
        text_model: config.textModel || undefined,
        vision_model: config.visionModel || undefined,
        disable_vision: config.disableVision,
        max_images_per_batch: config.maxImagesPerBatch ? parseInt(config.maxImagesPerBatch, 10) : undefined,
        image_max_size: config.imageMaxSize ? parseInt(config.imageMaxSize, 10) : undefined,
        image_quality: config.imageQuality ? parseInt(config.imageQuality, 10) : undefined,
        max_section_chars: config.maxSectionChars ? parseInt(config.maxSectionChars, 10) : undefined,
    };
}

export function subscribeConfig(handler) {
    const listener = (event) => {
        handler(event.detail);
    };

    window.addEventListener("config:updated", listener);

    // Emit current state immediately for convenience
    handler(getConfig());

    return () => {
        window.removeEventListener("config:updated", listener);
    };
}
