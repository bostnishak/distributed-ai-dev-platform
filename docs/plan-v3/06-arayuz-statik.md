# Parça 6 — Arayüz statik tarama bulguları

## XSS · JS: innerHTML atamaları

#### XSS-01 · js/assistant.js:102 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:102 — innerHTML ataması: `els.messages.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-02 · js/assistant.js:129 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:129 — innerHTML ataması: `els.messages.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-03 · js/assistant.js:177 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:177 — innerHTML ataması: `else bubble.innerHTML = renderMarkdown(text);`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-04 · js/assistant.js:241 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:241 — innerHTML ataması: `streamBar.innerHTML = '<span class="sp-think-ring sm"></span><span class="sp-stream-text">`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-05 · js/assistant.js:248 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:248 — innerHTML ataması: `bubble.innerHTML = `<div class="sp-think-head"><span class="sp-think-ring"></span><span cl`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-06 · js/assistant.js:264 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:264 — innerHTML ataması: `thinkLabelEl.innerHTML = `${stages[stageIdx]}<span class="sp-think-dots"><i></i><i></i><i>`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-07 · js/assistant.js:329 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:329 — innerHTML ataması: `bubble.innerHTML = renderMarkdown(fullText);`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-08 · js/assistant.js:349 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:349 — innerHTML ataması: `bubble.innerHTML = renderMarkdown(fullText);`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-09 · js/assistant.js:368 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:368 — innerHTML ataması: `det.innerHTML = `<summary style="cursor:pointer;font-weight:600;font-size:12.5px;">Ajan Ko`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-10 · js/assistant.js:389 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:389 — innerHTML ataması: `bubble.innerHTML = renderMarkdown(fullText);`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-11 · js/assistant_hero.js:126 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_hero.js:126 — innerHTML ataması: `els.heroCards.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-12 · js/assistant_hero.js:131 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_hero.js:131 — innerHTML ataması: `btn.innerHTML = ``.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-13 · js/assistant_history.js:84 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_history.js:84 — innerHTML ataması: `els.chatList.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-14 · js/assistant_ide_card.js:30 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:30 — innerHTML ataması: `dots.innerHTML = '<span class="dot-r"></span><span class="dot-y"></span><span class="dot-g`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-15 · js/assistant_ide_card.js:123 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:123 — innerHTML ataması: `verSelect.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-16 · js/assistant_ide_card.js:178 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:178 — innerHTML ataması: `rootHeader.innerHTML = `<span class="ide-chev">▾</span> <span>${(wsMeta.name || wsId).toUp`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-17 · js/assistant_ide_card.js:264 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:264 — innerHTML ataması: `statusLeft.innerHTML = '<span>⎇ main</span><span>✓ 0 hata</span>';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-18 · js/assistant_ide_card.js:293 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:293 — innerHTML ataması: `gutter.innerHTML = lines.map((_, i) => `<div>${i + 1}</div>`).join('');`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-19 · js/assistant_ide_card.js:294 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:294 — innerHTML ataması: `codeBlock.innerHTML = highlightCodeHtml(activeContent, path);`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-20 · js/assistant_ide_card.js:298 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:298 — innerHTML ataması: `breadcrumb.innerHTML = `<span class="bc-root">${wsMeta.name || wsId}</span> › ` + (path ||`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-21 · js/assistant_ide_card.js:302 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:302 — innerHTML ataması: `tabBar.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-22 · js/assistant_ide_card.js:308 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:308 — innerHTML ataması: `iconSpan.innerHTML = wsSvgIcon(fname, false);`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-23 · js/assistant_ide_card.js:348 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:348 — innerHTML ataması: `treeContainer.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-24 · js/assistant_ide_card.js:357 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:357 — innerHTML ataması: `row.innerHTML = `${chev}${wsSvgIcon(node.name, isDir, !isCollapsed)}<span class="ide-node-`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-25 · js/assistant_ide_card.js:390 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:390 — innerHTML ataması: `gutter.innerHTML = lines.map((_, i) => `<div>${i + 1}</div>`).join('');`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-26 · js/assistant_ide_card.js:391 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:391 — innerHTML ataması: `codeBlock.innerHTML = lines.map((ln) => {`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-27 · js/assistant_ide_card.js:414 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:414 — innerHTML ataması: `statusLeft.innerHTML = `<span>⎇ main</span><span>${errCount + issueCount === 0 ? '✓ 0 hata`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-28 · js/assistant_voice.js:65 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:65 — innerHTML ataması: `statusPill.innerHTML = isLive`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-29 · js/assistant_voice.js:109 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:109 — innerHTML ataması: `statusPill.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-30 · js/auth_modal.js:16 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/auth_modal.js:16 — innerHTML ataması: `overlay.innerHTML = ``.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-31 · js/auth_modal.js:139 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/auth_modal.js:139 — innerHTML ataması: `btn.innerHTML =`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-32 · js/cnc.js:15 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/cnc.js:15 — innerHTML ataması: `root.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-33 · js/cnc.js:78 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/cnc.js:78 — innerHTML ataması: `jobsBar.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-34 · js/cnc.js:114 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/cnc.js:114 — innerHTML ataması: `workspace.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-35 · js/cnc.js:198 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/cnc.js:198 — innerHTML ataması: `tbody.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-36 · js/studio.js:30 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:30 — innerHTML ataması: `root.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-37 · js/studio.js:131 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:131 — innerHTML ataması: `consoleLog.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-38 · js/studio.js:190 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:190 — innerHTML ataması: `treeEl.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### XSS-39 · js/studio.js:248 innerHTML ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:248 — innerHTML ataması: `wsSelect.innerHTML = '';`.
- **Değişiklik:** Atanan değer kullanıcı veya sunucu verisi içeriyorsa `textContent`, `h()` yardımcısı veya DOMPurify kullan.
- **Kabul:** 40 saldırı örneğinden hiçbiri bu noktada çalışmaz (test); değer sabit ise gerekçeli not.
- **Meta:** P1 · S · Bağ: - · Durum: açık

## AGH · JS: hata yolu olmayan fetch çağrıları

#### AGH-01 · js/assistant.js:296 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:296 — hata yolu olmayan fetch: `const resp = await fetch('/api/assistant/chat/stream', { method: 'POST', body: formData, s`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-02 · js/assistant_history.js:50 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_history.js:50 — hata yolu olmayan fetch: `const resp = await fetch(`/api/user/${encodeURIComponent(uid)}/chats`);`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-03 · js/assistant_ide_card.js:65 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:65 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/launch-exe`, { method: 'POST' });`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-04 · js/assistant_ide_card.js:90 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:90 — hata yolu olmayan fetch: `const resp = await fetch(`/api/studio/workspaces/${wsId}/build-exe`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-05 · js/assistant_ide_card.js:118 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:118 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/history`);`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-06 · js/assistant_ide_card.js:137 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:137 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/restore/${v}`, { method: 'POST' });`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-07 · js/assistant_ide_card.js:339 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:339 — hata yolu olmayan fetch: `const resp = await fetch(`/api/studio/workspaces/${wsId}/file?path=${encodeURIComponent(pa`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-08 · js/assistant_ide_card.js:387 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:387 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/diff?path=${encodeURIComponent(activ`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-09 · js/assistant_ide_card.js:432 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:432 — hata yolu olmayan fetch: `await fetch(`/api/studio/workspaces/${wsId}/file`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-10 · js/assistant_ide_card.js:448 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:448 — hata yolu olmayan fetch: `await fetch(`/api/studio/workspaces/${wsId}/file`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-11 · js/assistant_ide_card.js:451 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:451 — hata yolu olmayan fetch: `const tResp = await fetch(`/api/studio/workspaces/${wsId}/tree`);`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-12 · js/assistant_ide_render.js:86 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:86 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/exec`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-13 · js/assistant_ide_render.js:116 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:116 — hata yolu olmayan fetch: `await fetch(`/api/studio/workspaces/${wsId}/git`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-14 · js/assistant_ide_render.js:121 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:121 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/git`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-15 · js/assistant_ide_render.js:139 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:139 — hata yolu olmayan fetch: `const r = await fetch(`/api/studio/workspaces/${wsId}/search?q=${encodeURIComponent(q.trim`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-16 · js/assistant_ide_render.js:171 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:171 — hata yolu olmayan fetch: `const resp = await fetch(`/api/studio/workspaces/${wsId}/iterate`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-17 · js/assistant_voice.js:80 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:80 — hata yolu olmayan fetch: `const resp = await fetch('/api/assistant/transcribe', { method: 'POST', body: fd });`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-18 · js/assistant_voice.js:197 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:197 — hata yolu olmayan fetch: `const resp = await fetch('/api/assistant/config');`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-19 · js/assistant_voice.js:219 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:219 — hata yolu olmayan fetch: `const resp = await fetch('/api/assistant/run-code', {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-20 · js/auth_modal.js:51 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/auth_modal.js:51 — hata yolu olmayan fetch: `const resp = await fetch('/api/auth/status');`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-21 · js/auth_modal.js:105 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/auth_modal.js:105 — hata yolu olmayan fetch: `const r = await fetch(endpoint, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-22 · js/auth_modal.js:123 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/auth_modal.js:123 — hata yolu olmayan fetch: `await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-23 · js/hub.js:126 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/hub.js:126 — hata yolu olmayan fetch: `const resp = await fetch(url, init);`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-24 · js/hub.js:165 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/hub.js:165 — hata yolu olmayan fetch: `if (!spec) spec = await (await fetch('/openapi.json')).json();`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-25 · js/panels.js:95 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/panels.js:95 — hata yolu olmayan fetch: `const resp = await fetch('/api/rag/ingest-file', { method: 'POST', body });`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-26 · js/studio.js:396 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:396 — hata yolu olmayan fetch: `const resp = await fetch('/api/studio/generate', {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-27 · js/studio.js:417 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:417 — hata yolu olmayan fetch: `const resp = await fetch(`/api/studio/workspaces/${activeWsId}/iterate`, {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-28 · js/util.js:72 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/util.js:72 — hata yolu olmayan fetch: `const resp = await fetch(path, { ...options, headers });`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-29 · js/ux_shell.js:51 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/ux_shell.js:51 — hata yolu olmayan fetch: `const resp = await fetch('/api/orchestrator/feedback', {`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AGH-30 · js/ux_shell.js:60 hata yolu olmayan fetch
- **Sorun:** [DOĞRULANDI: F202] master/static/js/ux_shell.js:60 — hata yolu olmayan fetch: `const resp = await fetch('/api/ux/health-wizard');`.
- **Değişiklik:** `api()` yardımcısına geçir veya try/catch ile kullanıcıya nedenli hata göster.
- **Kabul:** Ağ kesildiğinde bu akış 'Failed to fetch' yerine eyleme dönük mesaj gösterir (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

## JSD · JS/CSS/HTML: diğer bulgular

#### JSD-01 · js/app.js:92 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/app.js:92 — temizlenmeyen global dinleyici: `window.addEventListener('hashchange', route);`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-02 · js/assistant.js:474 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:474 — temizlenmeyen global dinleyici: `document.addEventListener('open-saved-chat', (e) => {`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-03 · js/assistant.js:480 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:480 — temizlenmeyen global dinleyici: `document.addEventListener('chats-wiped', () => {`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-04 · js/message_tools.js:63 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/message_tools.js:63 — temizlenmeyen global dinleyici: `document.addEventListener('visibilitychange', restore);`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-05 · js/palette.js:70 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/palette.js:70 — temizlenmeyen global dinleyici: `document.addEventListener('keydown', (e) => {`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-06 · js/personal.js:466 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:466 — temizlenmeyen global dinleyici: `document.addEventListener('keydown', onKey);`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-07 · js/personal.js:489 temizlenmeyen global dinleyici
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:489 — temizlenmeyen global dinleyici: `document.addEventListener('usage-updated', refreshMonthTokens);`.
- **Değişiklik:** Dinleyiciyi `AbortController` ile sayfa ömrüne bağla.
- **Kabul:** Sayfa değişince dinleyici kaldırılır (sızıntı testi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-08 · js/assistant_ide_card.js:445 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:445 — engelleyici alert/confirm/prompt: `const rel = prompt('Yeni dosya yolu (ör. css/theme.css veya js/modal.js):');`.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-09 · js/assistant_ide_render.js:134 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:134 — engelleyici alert/confirm/prompt: `const q = prompt('Proje dosyalarında ara (Ctrl+Shift+F):');`.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-10 · js/cnc.js:157 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/cnc.js:157 — engelleyici alert/confirm/prompt: `const raw = prompt(`(${xPct}%, ${yPct}%) konumuna eklenecek CNC ölçüsü (ör. Ø25 H7, Ra 1.6`.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-11 · js/hub.js:94 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/hub.js:94 — engelleyici alert/confirm/prompt: `if (!window.confirm(`${method} ${path} kalıcı bir değişiklik yapabilir. Devam edilsin mi?``.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-12 · js/panels.js:124 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/panels.js:124 — engelleyici alert/confirm/prompt: `if (!window.confirm(`${d.title || d.doc_id} silinsin mi?`)) return;`.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-13 · js/personal_sections.js:116 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal_sections.js:116 — engelleyici alert/confirm/prompt: `const pwd = prompt('Şifreli AES-256 yedek için parola belirleyin (boş bırakırsanız yerel a`.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-14 · js/personal_sections.js:167 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal_sections.js:167 — engelleyici alert/confirm/prompt: `const rawArgs = prompt(`"${t.name}" aracı için JSON argümanları (boş bırakabilirsiniz):`, `.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-15 · js/studio.js:290 engelleyici alert/confirm/prompt
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:290 — engelleyici alert/confirm/prompt: `const rel = prompt('Yeni dosya yolu (ör. js/utils.js veya game/levels.py):');`.
- **Değişiklik:** Erişilebilir modal bileşeniyle değiştir.
- **Kabul:** Odak tuzaklı modal kullanılır; klavye ile onaylanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-16 · index.html:27 type'sız düğme
- **Sorun:** [DOĞRULANDI: F202] master/static/index.html:27 — type'sız düğme: `<button id="sidebarToggle" aria-label="Menüyü aç/kapat">`.
- **Değişiklik:** `type="button"` ekle.
- **Kabul:** Form içinde yanlışlıkla gönderim olmaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-17 · index.html:57 type'sız düğme
- **Sorun:** [DOĞRULANDI: F202] master/static/index.html:57 — type'sız düğme: `<button id="newChatBtn">`.
- **Değişiklik:** `type="button"` ekle.
- **Kabul:** Form içinde yanlışlıkla gönderim olmaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-18 · index.html:91 type'sız düğme
- **Sorun:** [DOĞRULANDI: F202] master/static/index.html:91 — type'sız düğme: `<button id="attachBtn" title="Dosya, görsel, ses veya çizim ekle">`.
- **Değişiklik:** `type="button"` ekle.
- **Kabul:** Form içinde yanlışlıkla gönderim olmaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-19 · index.html:96 type'sız düğme
- **Sorun:** [DOĞRULANDI: F202] master/static/index.html:96 — type'sız düğme: `<button id="sendBtn">`.
- **Değişiklik:** `type="button"` ekle.
- **Kabul:** Form içinde yanlışlıkla gönderim olmaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-20 · css/app.css:1 çok fazla !important
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:1 — çok fazla !important: `875 satır, 11 !important`.
- **Değişiklik:** Özgüllüğü düzenle.
- **Kabul:** !important sayısı ≤ 5.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-21 · css/theme.css:1 çok fazla !important
- **Sorun:** [DOĞRULANDI: F202] master/static/css/theme.css:1 — çok fazla !important: `480 satır, 11 !important`.
- **Değişiklik:** Özgüllüğü düzenle.
- **Kabul:** !important sayısı ≤ 5.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-22 · js/assistant_ide_render.js:49 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:49 — gevşek eşitlik (==): `html = html.replace(/\b([a-zA-Z-]+)(?==)/g, '<span class="hl-attr">$1</span>');`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-23 · js/canvas_widgets.js:165 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/canvas_widgets.js:165 — gevşek eşitlik (==): `const mFlow = ln.match(/^([A-Za-z0-9_]+)(?:\["?([^"\]]+)"?\])?\s*(?:-->|->|---|==>|\|\|--o`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-24 · js/personal.js:168 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:168 — gevşek eşitlik (==): `if (n == null) return '—';`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-25 · js/personal.js:219 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:219 — gevşek eşitlik (==): `h('div', { class: 'sp-usercard-sub' }, monthTokens == null ? 'Kişisel alan ve ayarlar' : ``.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-26 · js/studio.js:23 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:23 — gevşek eşitlik (==): `if (bytes == null) return '';`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-27 · js/util.js:8 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/util.js:8 — gevşek eşitlik (==): `if (value == null || value === false) continue;`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-28 · js/util.js:20 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/util.js:20 — gevşek eşitlik (==): `if (child == null || child === false) continue;`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-29 · js/util.js:96 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/util.js:96 — gevşek eşitlik (==): `if (seconds == null) return '—';`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-30 · js/util.js:103 gevşek eşitlik (==)
- **Sorun:** [DOĞRULANDI: F202] master/static/js/util.js:103 — gevşek eşitlik (==): `return value == null ? '—' : Number(value).toLocaleString('tr-TR');`.
- **Değişiklik:** `===` kullan.
- **Kabul:** Satır `===` kullanır; davranış testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-31 · js/assistant.js:492 çok uzun JS modülü
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:492 — çok uzun JS modülü: `492 satır`.
- **Değişiklik:** Modülü sorumluluklarına göre ayır.
- **Kabul:** Modül ≤ 400 satır; dışa aktarılan API aynı.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-32 · js/assistant_ide_card.js:485 çok uzun JS modülü
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:485 — çok uzun JS modülü: `485 satır`.
- **Değişiklik:** Modülü sorumluluklarına göre ayır.
- **Kabul:** Modül ≤ 400 satır; dışa aktarılan API aynı.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-33 · js/personal.js:492 çok uzun JS modülü
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:492 — çok uzun JS modülü: `492 satır`.
- **Değişiklik:** Modülü sorumluluklarına göre ayır.
- **Kabul:** Modül ≤ 400 satır; dışa aktarılan API aynı.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-34 · js/studio.js:440 çok uzun JS modülü
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:440 — çok uzun JS modülü: `440 satır`.
- **Değişiklik:** Modülü sorumluluklarına göre ayır.
- **Kabul:** Modül ≤ 400 satır; dışa aktarılan API aynı.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-35 · css/app.css:129 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:129 — odak halkası kaldırılmış: `outline: none;`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-36 · css/app.css:323 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:323 — odak halkası kaldırılmış: `outline: none; resize: none; font-size: 14.5px;`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-37 · css/app.css:451 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:451 — odak halkası kaldırılmış: `outline: none; }`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-38 · css/app.css:516 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:516 — odak halkası kaldırılmış: `outline: none;`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-39 · css/app.css:541 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:541 — odak halkası kaldırılmış: `outline: none; }`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-40 · css/app.css:752 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:752 — odak halkası kaldırılmış: `outline: none;`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-41 · css/app.css:796 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:796 — odak halkası kaldırılmış: `outline: none; }`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-42 · css/app.css:851 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:851 — odak halkası kaldırılmış: `outline: none; }`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-43 · css/theme.css:208 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/theme.css:208 — odak halkası kaldırılmış: `outline: none;`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-44 · css/theme.css:323 odak halkası kaldırılmış
- **Sorun:** [DOĞRULANDI: F202] master/static/css/theme.css:323 — odak halkası kaldırılmış: `outline: none; margin-bottom: 4px;`.
- **Değişiklik:** `outline:none` yerine görünür `:focus-visible` stili ver.
- **Kabul:** Klavye odağı bu öğede görünür (axe ve elle).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-45 · js/agents.js:126 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/agents.js:126 — çok uzun JS fonksiyonu: `export async function renderAgents(root, ctx) { (97 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-46 · js/assistant.js:205 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:205 — çok uzun JS fonksiyonu: `async function sendMessage(overridePrompt = null) { (206 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-47 · js/assistant_ide_card.js:10 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:10 — çok uzun JS fonksiyonu: `export function buildInlineWorkspaceCard(wsMeta, wsTree) { (476 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-48 · js/assistant_ide_render.js:62 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:62 — çok uzun JS fonksiyonu: `export function createTerminalDrawer(wsId, termToggleBtn, gitWsBtn, searchWsBtn) (91 satır`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-49 · js/assistant_voice.js:39 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:39 — çok uzun JS fonksiyonu: `export function initVoiceRecognition(els, updateSendState) { (155 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-50 · js/canvas_widgets.js:13 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/canvas_widgets.js:13 — çok uzun JS fonksiyonu: `export function renderChartSvg(specJson) { (129 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-51 · js/cnc.js:14 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/cnc.js:14 — çok uzun JS fonksiyonu: `export async function renderCnc(root) { (364 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-52 · js/markdown.js:35 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/markdown.js:35 — çok uzun JS fonksiyonu: `export function renderMarkdown(raw) { (94 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-53 · js/panels.js:101 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/panels.js:101 — çok uzun JS fonksiyonu: `export async function renderFiles(root, ctx) { (83 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-54 · js/personal_sections.js:4 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal_sections.js:4 — çok uzun JS fonksiyonu: `export async function renderSectionMemory(body, ctx) { (90 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-55 · js/personal_sections.js:148 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal_sections.js:148 — çok uzun JS fonksiyonu: `export async function renderSectionMcp(body, ctx) { (111 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-56 · js/projects.js:70 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/projects.js:70 — çok uzun JS fonksiyonu: `export function renderNewProject(root) { (109 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-57 · js/projects.js:229 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/projects.js:229 — çok uzun JS fonksiyonu: `export async function renderProjectDetail(root, id, ctx) { (161 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-58 · js/studio.js:29 çok uzun JS fonksiyonu
- **Sorun:** [DOĞRULANDI: F202] master/static/js/studio.js:29 — çok uzun JS fonksiyonu: `export async function renderStudio(root) { (412 satır)`.
- **Değişiklik:** Fonksiyonu bileşenlere böl.
- **Kabul:** Fonksiyon ≤ 80 satır; ilgili arayüz testi geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### JSD-59 · js/personal_sections.js:223 sabit http adresi
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal_sections.js:223 — sabit http adresi: `const urlIn = h('input', { class: 'sp-input', type: 'url', placeholder: 'MCP Sunucu URL (ö`.
- **Değişiklik:** Yapılandırmaya taşı.
- **Kabul:** Adres yapılandırmadan okunur.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-60 · js/assistant.js:143 cssText ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:143 — cssText ataması: `wrap.style.cssText = 'display:flex;flex-direction:column;align-items:flex-end;max-width:65`.
- **Değişiklik:** CSS sınıfına taşı.
- **Kabul:** Satır sınıf kullanır.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-61 · js/assistant_ide_render.js:64 cssText ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:64 — cssText ataması: `termDrawer.style.cssText = 'background:#0d1017;border-top:1px solid #2b2b36;padding:8px 12`.
- **Değişiklik:** CSS sınıfına taşı.
- **Kabul:** Satır sınıf kullanır.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-62 · js/assistant_ide_render.js:67 cssText ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:67 — cssText ataması: `termOut.style.cssText = 'margin:0 0 6px;max-height:150px;overflow-y:auto;white-space:pre-w`.
- **Değişiklik:** CSS sınıfına taşı.
- **Kabul:** Satır sınıf kullanır.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-63 · js/assistant_ide_render.js:70 cssText ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:70 — cssText ataması: `termRow.style.cssText = 'display:flex;gap:6px;align-items:center;';`.
- **Değişiklik:** CSS sınıfına taşı.
- **Kabul:** Satır sınıf kullanır.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-64 · js/assistant_ide_render.js:74 cssText ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_render.js:74 — cssText ataması: `termIn.style.cssText = 'flex:1;background:#161b26;border:1px solid #334155;color:#f8fafc;b`.
- **Değişiklik:** CSS sınıfına taşı.
- **Kabul:** Satır sınıf kullanır.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-65 · js/auth_modal.js:13 cssText ataması
- **Sorun:** [DOĞRULANDI: F202] master/static/js/auth_modal.js:13 — cssText ataması: `overlay.style.cssText =`.
- **Değişiklik:** CSS sınıfına taşı.
- **Kabul:** Satır sınıf kullanır.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-66 · js/assistant.js:360 insertAdjacentHTML
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:360 — insertAdjacentHTML: `badgeRow.insertAdjacentHTML('beforeend', ' ' + renderConfidenceBadgeHtml(verificationInfo.`.
- **Değişiklik:** Sanitizer'dan geçir veya DOM API kullan.
- **Kabul:** Saldırı örneği çalışmaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### JSD-67 · js/assistant.js:100 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:100 — doğrudan localStorage: `try { localStorage.setItem(storageKeys().lastChatKey, id); } catch { /* ignore */ }`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-68 · js/assistant_history.js:14 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_history.js:14 — doğrudan localStorage: `return JSON.parse(localStorage.getItem(storageKeys().storageKey) || '{}');`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-69 · js/assistant_history.js:22 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_history.js:22 — doğrudan localStorage: `localStorage.setItem(storageKeys().storageKey, JSON.stringify(chats));`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-70 · js/assistant_history.js:35 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_history.js:35 — doğrudan localStorage: `try { localStorage.setItem(storageKeys().lastChatKey, chatId); } catch { /* ignore */ }`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-71 · js/assistant_history.js:74 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_history.js:74 — doğrudan localStorage: `const lastId = localStorage.getItem(storageKeys().lastChatKey);`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-72 · js/personal.js:21 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:21 — doğrudan localStorage: `let activeUserId = localStorage.getItem(LS_USER) || 'default';`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-73 · js/personal.js:30 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:30 — doğrudan localStorage: `try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(LS_PREFS) || '{}') }; } cat`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-74 · js/personal.js:70 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:70 — doğrudan localStorage: `try { localStorage.setItem(LS_PREFS, JSON.stringify(s)); } catch { /* storage unavailable `.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-75 · js/personal.js:345 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/personal.js:345 — doğrudan localStorage: `localStorage.setItem(LS_USER, uid);`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-76 · js/store.js:20 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/store.js:20 — doğrudan localStorage: `return window.localStorage.getItem(key);`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-77 · js/store.js:28 doğrudan localStorage
- **Sorun:** [DOĞRULANDI: F202] master/static/js/store.js:28 — doğrudan localStorage: `window.localStorage.setItem(key, value);`.
- **Değişiklik:** Depolama yardımcısına (try/catch, şema sürümü) geçir.
- **Kabul:** Depolama kapalıyken bu akış çalışır (test).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-78 · js/assistant.js:465 sihirli zaman aşımı sayısı
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:465 — sihirli zaman aşımı sayısı: `setTimeout(() => { copyBtn.textContent = 'Kopyala'; copyBtn.classList.remove('copied'); },`.
- **Değişiklik:** Adlandırılmış sabite çıkar.
- **Kabul:** Sabit adı belgelidir.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-79 · js/assistant_hero.js:39 sihirli zaman aşımı sayısı
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_hero.js:39 — sihirli zaman aşımı sayısı: `setTimeout(() => { copyBtn.textContent = 'Kopyala'; }, 1600);`.
- **Değişiklik:** Adlandırılmış sabite çıkar.
- **Kabul:** Sabit adı belgelidir.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-80 · js/assistant_ide_card.js:68 sihirli zaman aşımı sayısı
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:68 — sihirli zaman aşımı sayısı: `setTimeout(() => { launchBtn.disabled = false; launchBtn.textContent = 'EXE Çalıştır'; }, `.
- **Değişiklik:** Adlandırılmış sabite çıkar.
- **Kabul:** Sabit adı belgelidir.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-81 · js/assistant_ide_card.js:376 sihirli zaman aşımı sayısı
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_ide_card.js:376 — sihirli zaman aşımı sayısı: `setTimeout(() => { copyCodeBtn.textContent = 'Kopyala'; }, 1400);`.
- **Değişiklik:** Adlandırılmış sabite çıkar.
- **Kabul:** Sabit adı belgelidir.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-82 · js/panels.js:11 sihirli zaman aşımı sayısı
- **Sorun:** [DOĞRULANDI: F202] master/static/js/panels.js:11 — sihirli zaman aşımı sayısı: `setTimeout(() => URL.revokeObjectURL(url), 2000);`.
- **Değişiklik:** Adlandırılmış sabite çıkar.
- **Kabul:** Sabit adı belgelidir.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### JSD-83 · js/app.js:76 temizlenmeyen setInterval
- **Sorun:** [DOĞRULANDI: F202] master/static/js/app.js:76 — temizlenmeyen setInterval: `pollTimer = setInterval(async () => {`.
- **Değişiklik:** Sayfa kapanınca `clearInterval` çağır.
- **Kabul:** Sayfa değişince zamanlayıcı durur.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-84 · js/assistant.js:256 temizlenmeyen setInterval
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant.js:256 — temizlenmeyen setInterval: `const thinkTicker = setInterval(() => {`.
- **Değişiklik:** Sayfa kapanınca `clearInterval` çağır.
- **Kabul:** Sayfa değişince zamanlayıcı durur.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-85 · js/assistant_voice.js:175 temizlenmeyen setInterval
- **Sorun:** [DOĞRULANDI: F202] master/static/js/assistant_voice.js:175 — temizlenmeyen setInterval: `recTimer = setInterval(() => {`.
- **Değişiklik:** Sayfa kapanınca `clearInterval` çağır.
- **Kabul:** Sayfa değişince zamanlayıcı durur.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-86 · css/app.css:610 11px altı yazı
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:610 — 11px altı yazı: `font-size: 10px`.
- **Değişiklik:** En az 12px yap.
- **Kabul:** Yazı ≥ 12px.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-87 · css/app.css:679 11px altı yazı
- **Sorun:** [DOĞRULANDI: F202] master/static/css/app.css:679 — 11px altı yazı: `font-size: 9px`.
- **Değişiklik:** En az 12px yap.
- **Kabul:** Yazı ≥ 12px.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### JSD-88 · css/theme.css:270 11px altı yazı
- **Sorun:** [DOĞRULANDI: F202] master/static/css/theme.css:270 — 11px altı yazı: `font-size: 10px`.
- **Değişiklik:** En az 12px yap.
- **Kabul:** Yazı ≥ 12px.
- **Meta:** P2 · S · Bağ: - · Durum: açık
