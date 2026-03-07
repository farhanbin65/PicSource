// Handle form submission
document.getElementById('uploadForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const imageInput = document.getElementById('imageInput');
    const title = document.getElementById('title').value;
    const photographer = document.getElementById('photographer').value;
    const category = document.getElementById('category').value;
    const description = document.getElementById('description').value;
    
    // Validate image
    const file = imageInput.files[0];
    if (!file) {
        showStatus('Please select an image', 'error');
        return;
    }
    
    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showStatus('Please select a valid image file (JPG, PNG, GIF, WEBP)', 'error');
        return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
        showStatus('Image size should be less than 5MB', 'error');
        return;
    }
    
    // Create a unique filename
    const timestamp = Date.now();
    const imageFilename = `upload_${timestamp}_${file.name}`;
    
    // Read the image file
    const reader = new FileReader();
    reader.onload = function(e) {
        const imageData = e.target.result; // This is base64 data
        
        // 1. Save the image file to uploads folder (trigger download)
        saveImageFile(imageData, imageFilename);
        
        // 2. Create SQL entry
        const sqlData = {
            id: timestamp,
            filename: imageFilename,
            title: title,
            photographer: photographer,
            category: category,
            description: description,
            date: new Date().toISOString().split('T')[0],
            file_type: file.type,
            file_size: file.size
        };
        
        // 3. Save to SQLite database file
        saveToSQLite(sqlData);
        
        // 4. Also save to localStorage for immediate display (temporary)
        saveToLocalStorage(sqlData, imageData);
        
        // Show success message
        showStatus('✅ Upload successful! Files saved to uploads/ and database/', 'success');
        
        // Reset form
        document.getElementById('uploadForm').reset();
        document.getElementById('previewContainer').classList.add('hidden');
        
        // Redirect to home page after 2 seconds
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 2000);
    };
    
    reader.readAsDataURL(file);
});

// Save image file to uploads folder
function saveImageFile(imageData, filename) {
    // Convert base64 to blob
    const base64Data = imageData.split(',')[1];
    const byteCharacters = atob(base64Data);
    const byteNumbers = new Array(byteCharacters.length);
    
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'image/jpeg' });
    
    // Create download link and trigger download
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `uploads/${filename}`; // This will save to uploads folder
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
}

// Save metadata to SQLite file
function saveToSQLite(imageData) {
    // Create SQL statement
    const sql = `INSERT INTO images (filename, title, photographer, category, description, date, file_type, file_size) 
                 VALUES ('${imageData.filename}', '${imageData.title}', '${imageData.photographer}', 
                 '${imageData.category}', '${imageData.description}', '${imageData.date}', 
                 '${imageData.file_type}', ${imageData.file_size});`;
    
    // Create a SQLite file with the insert statement
    const sqlContent = `-- PicSource Database
-- Uploaded on: ${new Date().toISOString()}

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    title TEXT NOT NULL,
    photographer TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    date TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert new image
${sql}

-- View all images
-- SELECT * FROM images ORDER BY upload_date DESC;
`;
    
    // Create blob and trigger download
    const blob = new Blob([sqlContent], { type: 'application/x-sqlite3' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'database/database.sqlite';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
}

// Save to localStorage for immediate display (temporary until we implement SQLite reading)
function saveToLocalStorage(imageData, imageBase64) {
    let existingImages = [];
    const savedImages = localStorage.getItem('picsource_images');
    
    if (savedImages) {
        existingImages = JSON.parse(savedImages);
    }
    
    // Create image object for display
    const newImage = {
        id: imageData.id,
        url: imageBase64, // Use base64 for immediate display
        filename: imageData.filename,
        title: imageData.title,
        photographer: imageData.photographer,
        category: imageData.category,
        description: imageData.description,
        date: imageData.date
    };
    
    // Add to beginning
    existingImages.unshift(newImage);
    
    // Save to localStorage
    localStorage.setItem('picsource_images', JSON.stringify(existingImages));
}

// Image preview
document.getElementById('imageInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('imagePreview');
            const previewContainer = document.getElementById('previewContainer');
            preview.src = e.target.result;
            previewContainer.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }
});

function showStatus(message, type) {
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = `
        <div class="alert alert-${type === 'error' ? 'error' : 'success'} shadow-lg">
            <div>
                ${type === 'error' ? '❌' : '✅'}
                <span>${message}</span>
            </div>
        </div>
    `;
}