// f11.jsx
// Photoshop Script equivalent to f11.atn
// Crops document (Left: 108, Top: 28.8, Right: 900, Bottom: 820.8),
// saves 1.png on Desktop, fills non-transparent with black, saves 2.png on Desktop, and closes document.

#target photoshop

function main() {
    if (app.documents.length == 0) {
        alert("Không có tài liệu nào đang mở trong Photoshop.");
        return;
    }
    
    var doc = app.activeDocument;
    
    // Ghi nhận hệ thống thước đo hiện tại và chuyển sang Pixels
    var oldRulerUnits = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    
    try {
        // Nếu là background layer thì chuyển thành layer bình thường để thao tác
        if (doc.layers.length > 0 && doc.activeLayer.isBackgroundLayer) {
            doc.activeLayer.isBackgroundLayer = false;
        }

        // Cắt ảnh trực tiếp (Left, Top, Right, Bottom)
        // Bounds for crop: [108, 28.8, 900, 820.8]
        doc.crop([108, 28.8, 900, 820.8]);
        
        // Lưu thành 1.png trên Desktop
        var desktopPath = Folder.desktop.fsName;
        var file1 = new File(desktopPath + "/1.png");
        var pngSaveOptions = new PNGSaveOptions();
        doc.saveAs(file1, pngSaveOptions, true, Extension.LOWERCASE);
        
        // Tạo lớp phủ màu đen (2.png) bằng cách khóa điểm ảnh trong suốt và đổ màu đen
        var activeLayer = doc.activeLayer;
        activeLayer.transparentPixelsLocked = true;
        doc.selection.selectAll();
        
        var blackColor = new SolidColor();
        blackColor.rgb.red = 0;
        blackColor.rgb.green = 0;
        blackColor.rgb.blue = 0;
        
        doc.selection.fill(blackColor);
        doc.selection.deselect();
        
        // Lưu thành 2.png trên Desktop
        var file2 = new File(desktopPath + "/2.png");
        doc.saveAs(file2, pngSaveOptions, true, Extension.LOWERCASE);
        
        // Đóng tài liệu mà không lưu
        doc.close(SaveOptions.DONOTSAVECHANGES);
        
    } catch (e) {
        alert("Đã xảy ra lỗi: " + e.toString());
    } finally {
        // Trả lại thiết lập đơn vị đo cũ
        try {
            app.preferences.rulerUnits = oldRulerUnits;
        } catch(e) {}
    }
}

main();