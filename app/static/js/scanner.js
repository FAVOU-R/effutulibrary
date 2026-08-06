/* Barcode & QR Scanner Handler (html5-qrcode + USB Auto-Focus Listener) */

let html5QrCode = null;

function initCameraScanner(elementId, onScanSuccessCallback) {
  if (html5QrCode) {
    html5QrCode.stop().catch(err => console.log(err));
  }
  
  html5QrCode = new Html5Qrcode(elementId);
  const config = { fps: 10, qrbox: { width: 250, height: 250 } };

  html5QrCode.start(
    { facingMode: "environment" },
    config,
    (decodedText, decodedResult) => {
      console.log("Barcode Scanned:", decodedText);
      onScanSuccessCallback(decodedText);
      stopCameraScanner();
    },
    (errorMessage) => {
      // parse errors, ignore
    }
  ).catch(err => {
    alert("Unable to access camera: " + err);
  });
}

function stopCameraScanner() {
  if (html5QrCode) {
    html5QrCode.stop().then(() => {
      console.log("Scanner stopped");
    }).catch(err => console.log(err));
  }
}

/* USB Barcode Scanner Auto-Focus Listener */
let usbBuffer = "";
let lastKeyTime = Date.now();

document.addEventListener("keydown", function(e) {
  const currentTime = Date.now();
  if (currentTime - lastKeyTime > 100) {
    usbBuffer = "";
  }
  lastKeyTime = currentTime;

  if (e.key === "Enter") {
    if (usbBuffer.length > 5) {
      console.log("USB Scanner Input Detected:", usbBuffer);
      const activeElement = document.activeElement;
      if (activeElement && activeElement.dataset.scannerTarget === "isbn") {
        activeElement.value = usbBuffer;
        if (typeof onUSBScanComplete === "function") {
          onUSBScanComplete(usbBuffer);
        }
      } else if (typeof handleQRScanResult === "function") {
        handleQRScanResult(usbBuffer);
      }
      usbBuffer = "";
    }
  } else if (e.key.length === 1) {
    usbBuffer += e.key;
  }
});
