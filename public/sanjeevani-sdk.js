/**
 * Sanjeevani AI Telemedicine Integration SDK
 * Standardized embedding layer for external digital pharmacy & health apps.
 */
(function () {
  const SanjeevaniSDK = {
    init: function (config) {
      const targetElement = document.getElementById(config.elementId);
      if (!targetElement) {
        console.error("SanjeevaniSDK: Target container element not found with ID", config.elementId);
        return;
      }
      
      const theme = config.theme || "dark";
      const apiEndpoint = config.apiEndpoint || window.location.origin;
      const type = config.type || "prescription"; // 'medicine' or 'prescription'
      
      // Create embedded button
      const button = document.createElement("button");
      button.innerText = type === "prescription" ? "📋 Scan Prescription" : "💊 Verify Medicine Strip";
      button.style.backgroundColor = theme === "dark" ? "#0ea5e9" : "#0284c7";
      button.style.color = "#ffffff";
      button.style.border = "none";
      button.style.borderRadius = "0.75rem";
      button.style.padding = "0.625rem 1.25rem";
      button.style.fontSize = "0.875rem";
      button.style.fontWeight = "600";
      button.style.cursor = "pointer";
      button.style.display = "inline-flex";
      button.style.alignItems = "center";
      button.style.gap = "0.5rem";
      button.style.transition = "transform 0.15s, opacity 0.15s";
      
      button.onmouseover = () => {
        button.style.opacity = "0.9";
        button.style.transform = "scale(1.02)";
      };
      button.onmouseout = () => {
        button.style.opacity = "1";
        button.style.transform = "none";
      };

      // Modal Iframe construction on click
      button.onclick = () => {
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.backgroundColor = "rgba(0,0,0,0.7)";
        overlay.style.backdropFilter = "blur(4px)";
        overlay.style.zIndex = "99999";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.padding = "1.5rem";
        
        const modal = document.createElement("div");
        modal.style.width = "100%";
        modal.style.maxWidth = "30rem";
        modal.style.height = "85vh";
        modal.style.backgroundColor = "#09090b";
        modal.style.border = "1px solid #27272a";
        modal.style.borderRadius = "1.5rem";
        modal.style.overflow = "hidden";
        modal.style.display = "flex";
        modal.style.flexDirection = "column";

        const header = document.createElement("div");
        header.style.padding = "1rem 1.5rem";
        header.style.borderBottom = "1px solid #27272a";
        header.style.display = "flex";
        header.style.justifyContent = "space-between";
        header.style.alignItems = "center";
        
        const title = document.createElement("h3");
        title.innerText = "Sanjeevani AI - Scan Layer";
        title.style.color = "#ffffff";
        title.style.margin = "0";
        title.style.fontSize = "0.95rem";
        title.style.fontWeight = "600";
        title.style.fontFamily = "system-ui, sans-serif";
        
        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "&times;";
        closeBtn.style.background = "none";
        closeBtn.style.border = "none";
        closeBtn.style.color = "#a1a1aa";
        closeBtn.style.fontSize = "1.5rem";
        closeBtn.style.cursor = "pointer";
        closeBtn.style.padding = "0";
        closeBtn.style.lineHeight = "1";
        closeBtn.onclick = () => document.body.removeChild(overlay);

        header.appendChild(title);
        header.appendChild(closeBtn);

        const iframe = document.createElement("iframe");
        iframe.src = `${apiEndpoint}/scan?type=${type}&embed=true`;
        iframe.style.flex = "1";
        iframe.style.width = "100%";
        iframe.style.border = "none";
        
        modal.appendChild(header);
        modal.appendChild(iframe);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Listen for postMessage payload mapping
        const messageHandler = function (event) {
          if (event.origin !== apiEndpoint) return;
          if (event.data && event.data.type === "SANJEEVANI_RESULT") {
            if (config.onSuccess) {
              config.onSuccess(event.data.payload);
            }
            try {
              document.body.removeChild(overlay);
            } catch (e) {}
            window.removeEventListener("message", messageHandler);
          }
        };
        window.addEventListener("message", messageHandler);
      };

      targetElement.appendChild(button);
    }
  };

  window.SanjeevaniSDK = SanjeevaniSDK;
})();
