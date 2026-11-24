// EPK-34: MV3 service worker registering context menu & side panel with zero automatic page exfiltration.
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'dadp-ask-selection',
    title: "DADP Asistan'a Sor (Yerel)",
    contexts: ['selection'],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'dadp-ask-selection' && info.selectionText) {
    chrome.storage.local.set({ pendingSelection: info.selectionText.slice(0, 8000) });
    if (tab && tab.windowId && chrome.sidePanel && chrome.sidePanel.open) {
      chrome.sidePanel.open({ windowId: tab.windowId });
    }
  }
});
