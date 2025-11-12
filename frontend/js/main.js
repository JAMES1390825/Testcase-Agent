import { initialiseConfigStore, subscribeConfig } from "./configStore.js";
import { initConfigTab } from "./configTab.js";
import { initGenerationTab } from "./generationTab.js";
import { initEnhanceTab } from "./enhanceTab.js";

function showTab(tabId) {
    document.querySelectorAll(".tab-pane").forEach((pane) => {
        pane.classList.toggle("active", pane.id === tabId);
    });

    document.querySelectorAll(".tab-link").forEach((link) => {
        link.classList.toggle("active", link.dataset.target === tabId);
    });
}

function initTabs() {
    document.querySelectorAll(".tab-link").forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            showTab(link.dataset.target);
        });
    });
}

function initVisionToggle() {
    const visionHints = document.querySelectorAll(".vision-required");
    subscribeConfig((config) => {
        visionHints.forEach((el) => {
            el.classList.toggle("hidden", config.disableVision);
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initialiseConfigStore();
    initTabs();
    initConfigTab();
    initGenerationTab();
    initEnhanceTab();
    initVisionToggle();

    const defaultTab = document.querySelector(".tab-link.active");
    if (defaultTab) {
        showTab(defaultTab.dataset.target);
    }
});
