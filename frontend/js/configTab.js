import { getConfig, setConfigValue, subscribeConfig, persistCurrentConfig } from "./configStore.js";

function toggleVisionParams(containers, disableVision) {
    containers.forEach((container) => {
        if (disableVision) {
            container.classList.add("hidden");
        } else {
            container.classList.remove("hidden");
        }
    });
}

export function initConfigTab() {
    const apiKeyInput = document.getElementById("configApiKey");
    const baseUrlInput = document.getElementById("configBaseUrl");
    const textModelInput = document.getElementById("configTextModel");
    const visionModelInput = document.getElementById("configVisionModel");
    const disableVisionSwitch = document.getElementById("configDisableVision");
    const maxImagesInput = document.getElementById("configMaxImagesPerBatch");
    const imageSizeInput = document.getElementById("configImageMaxSize");
    const imageQualityInput = document.getElementById("configImageQuality");
    const maxSectionCharsInput = document.getElementById("configMaxSectionChars");
    const visionParamBlocks = Array.from(document.querySelectorAll(".vision-params"));
    const saveButton = document.getElementById("configSave");

    const bind = (input, key) => {
        if (!input) return;
        input.addEventListener("change", () => {
            setConfigValue(key, input.type === "checkbox" ? input.checked : input.value.trim());
        });
        input.addEventListener("blur", () => {
            setConfigValue(key, input.type === "checkbox" ? input.checked : input.value.trim());
        });
    };

    const commitConfigValues = () => {
        if (apiKeyInput) setConfigValue("apiKey", apiKeyInput.value.trim());
        if (baseUrlInput) setConfigValue("baseUrl", baseUrlInput.value.trim());
        if (textModelInput) setConfigValue("textModel", textModelInput.value.trim());
        if (visionModelInput) setConfigValue("visionModel", visionModelInput.value.trim());
        if (disableVisionSwitch) setConfigValue("disableVision", disableVisionSwitch.checked);
        if (maxImagesInput) setConfigValue("maxImagesPerBatch", maxImagesInput.value.trim());
        if (imageSizeInput) setConfigValue("imageMaxSize", imageSizeInput.value.trim());
        if (imageQualityInput) setConfigValue("imageQuality", imageQualityInput.value.trim());
        if (maxSectionCharsInput) setConfigValue("maxSectionChars", maxSectionCharsInput.value.trim());
    };

    subscribeConfig((config) => {
        if (apiKeyInput) apiKeyInput.value = config.apiKey;
        if (baseUrlInput) baseUrlInput.value = config.baseUrl;
        if (textModelInput) textModelInput.value = config.textModel;
        if (visionModelInput) visionModelInput.value = config.visionModel;
        if (disableVisionSwitch) disableVisionSwitch.checked = config.disableVision;
        if (maxImagesInput) maxImagesInput.value = config.maxImagesPerBatch;
        if (imageSizeInput) imageSizeInput.value = config.imageMaxSize;
        if (imageQualityInput) imageQualityInput.value = config.imageQuality;
        if (maxSectionCharsInput) maxSectionCharsInput.value = config.maxSectionChars;
        toggleVisionParams(visionParamBlocks, config.disableVision);
    });

    bind(apiKeyInput, "apiKey");
    bind(baseUrlInput, "baseUrl");
    bind(textModelInput, "textModel");
    bind(visionModelInput, "visionModel");
    bind(maxImagesInput, "maxImagesPerBatch");
    bind(imageSizeInput, "imageMaxSize");
    bind(imageQualityInput, "imageQuality");
    bind(maxSectionCharsInput, "maxSectionChars");

    if (disableVisionSwitch) {
        disableVisionSwitch.addEventListener("change", () => {
            setConfigValue("disableVision", disableVisionSwitch.checked);
            toggleVisionParams(visionParamBlocks, disableVisionSwitch.checked);
        });
    }


    if (saveButton) {
        saveButton.addEventListener("click", () => {
            commitConfigValues();
            persistCurrentConfig();
            saveButton.textContent = "已保存";
            setTimeout(() => {
                saveButton.textContent = "保存配置";
            }, 1600);
        });
    }

    const exportEnvButton = document.getElementById("configExportEnv");
    if (exportEnvButton) {
        exportEnvButton.addEventListener("click", () => {
            const cfg = getConfig();
            const envText = [
                `OPENAI_API_KEY=${cfg.apiKey}`,
                `OPENAI_BASE_URL=${cfg.baseUrl}`,
                `TEXT_MODEL_NAME=${cfg.textModel}`,
                `VISION_MODEL_NAME=${cfg.visionModel}`,
                `DISABLE_VISION=${cfg.disableVision ? "1" : "0"}`,
                `MAX_IMAGES_PER_BATCH=${cfg.maxImagesPerBatch}`,
                `IMAGE_MAX_SIZE=${cfg.imageMaxSize}`,
                `IMAGE_QUALITY=${cfg.imageQuality}`,
                `MAX_SECTION_CHARS=${cfg.maxSectionChars}`,
            ].join("\n");

            navigator.clipboard
                .writeText(envText)
                .then(() => {
                    exportEnvButton.textContent = "已复制到剪贴板";
                    setTimeout(() => {
                        exportEnvButton.textContent = "复制为 .env";
                    }, 1800);
                })
                .catch(() => {
                    alert("无法复制到剪贴板，请手动复制。");
                });
        });
    }
}
