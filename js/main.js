// Sample images from Picsum
const sampleImages = [
    {
        id: 1015,
        url: 'https://picsum.photos/id/1015/400/300',
        title: 'Mountain View',
        photographer: 'John Doe',
        category: 'Nature',
        date: '2024-01-15'
    },
    {
        id: 1018,
        url: 'https://picsum.photos/id/1018/400/300',
        title: 'Valley',
        photographer: 'Jane Smith',
        category: 'Nature',
        date: '2024-02-20'
    },
    {
        id: 1043,
        url: 'https://picsum.photos/id/1043/400/300',
        title: 'River',
        photographer: 'Mike Johnson',
        category: 'Nature',
        date: '2024-03-10'
    },
    {
        id: 100,
        url: 'https://picsum.photos/id/100/400/300',
        title: 'Lake',
        photographer: 'Sarah Wilson',
        category: 'Landscape',
        date: '2024-01-05'
    },
    {
        id: 101,
        url: 'https://picsum.photos/id/101/400/300',
        title: 'City',
        photographer: 'Chris Brown',
        category: 'Urban',
        date: '2024-02-28'
    },
    {
        id: 102,
        url: 'https://picsum.photos/id/102/400/300',
        title: 'Forest',
        photographer: 'Emily Davis',
        category: 'Nature',
        date: '2024-03-01'
    },
    {
        id: 103,
        url: 'https://picsum.photos/id/103/400/300',
        title: 'Ocean',
        photographer: 'Alex Turner',
        category: 'Ocean',
        date: '2024-03-12'
    },
    {
        id: 104,
        url: 'https://picsum.photos/id/104/400/300',
        title: 'Waterfall',
        photographer: 'Taylor Swift',
        category: 'Nature',
        date: '2024-02-14'
    },
    {
        id: 106,
        url: 'https://picsum.photos/id/106/400/300',
        title: 'Flowers',
        photographer: 'Emma Watson',
        category: 'Nature',
        date: '2024-03-15'
    },
    {
        id: 107,
        url: 'https://picsum.photos/id/107/400/300',
        title: 'Beach',
        photographer: 'James Cameron',
        category: 'Ocean',
        date: '2024-03-18'
    },
    {
        id: 108,
        url: 'https://picsum.photos/id/108/400/300',
        title: 'Desert',
        photographer: 'Robert Johnson',
        category: 'Travel',
        date: '2024-03-20'
    },
    {
        id: 109,
        url: 'https://picsum.photos/id/109/400/300',
        title: 'Mountain Lake',
        photographer: 'Lisa Ray',
        category: 'Nature',
        date: '2024-03-22'
    }
];

// Store all images
let allImages = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadImages();
});

function loadImages() {
    // For now, we'll use localStorage to display uploaded images
    // In a production environment, you'd need a server to read the SQLite file
    const savedImages = localStorage.getItem('picsource_images');
    
    if (savedImages) {
        // Parse the saved images
        const uploadedImages = JSON.parse(savedImages);
        // Combine with sample images (uploaded first)
        allImages = [...uploadedImages, ...sampleImages];
    } else {
        allImages = [...sampleImages];
    }
    
    displayImages();
}

function displayImages() {
    const gallery = document.getElementById('gallery');
    if (!gallery) return;

    gallery.innerHTML = '';
    
    if (allImages.length === 0) {
        gallery.innerHTML = '<div class="col-span-full text-center py-8">No images found</div>';
        return;
    }
    
    allImages.forEach(image => {
        const card = document.createElement('div');
        card.className = 'image-card card bg-base-100 shadow-xl overflow-hidden relative';
        
        // Check if it's an uploaded image (has filename property)
        const isUploaded = image.filename ? true : false;
        
        card.innerHTML = `
            <figure class="relative h-64">
                <img src="${image.url}" alt="${image.title}" class="w-full h-full object-cover">
                <div class="metadata-overlay absolute bottom-0 left-0 right-0 p-4 text-white">
                    <h3 class="font-bold text-lg truncate">${image.title}</h3>
                    <p class="text-sm"><i class="fa-solid fa-camera mr-1"></i> ${image.photographer}</p>
                    <p class="text-sm"><i class="fa-regular fa-calendar mr-1"></i> ${image.date}</p>
                    <p class="text-sm"><i class="fa-regular fa-folder mr-1"></i> ${image.category}</p>
                    ${isUploaded ? '<p class="text-xs mt-1"><i class="fa-solid fa-floppy-disk mr-1"></i> Saved to disk</p>' : ''}
                </div>
            </figure>
        `;
        gallery.appendChild(card);
    });
}

window.searchImages = function() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    if (!searchTerm) {
        loadImages();
        return;
    }
    
    const filtered = allImages.filter(img => 
        img.title.toLowerCase().includes(searchTerm) ||
        img.photographer.toLowerCase().includes(searchTerm) ||
        img.category.toLowerCase().includes(searchTerm)
    );
    
    const gallery = document.getElementById('gallery');
    gallery.innerHTML = '';
    
    if (filtered.length === 0) {
        gallery.innerHTML = '<div class="col-span-full text-center py-8">No images match your search</div>';
        return;
    }
    
    filtered.forEach(image => {
        const card = document.createElement('div');
        card.className = 'image-card card bg-base-100 shadow-xl overflow-hidden relative';
        const isUploaded = image.filename ? true : false;
        
        card.innerHTML = `
            <figure class="relative h-64">
                <img src="${image.url}" alt="${image.title}" class="w-full h-full object-cover">
                <div class="metadata-overlay absolute bottom-0 left-0 right-0 p-4 text-white">
                    <h3 class="font-bold text-lg truncate">${image.title}</h3>
                    <p class="text-sm"><i class="fa-solid fa-camera mr-1"></i> ${image.photographer}</p>
                    <p class="text-sm"><i class="fa-regular fa-calendar mr-1"></i> ${image.date}</p>
                    <p class="text-sm"><i class="fa-regular fa-folder mr-1"></i> ${image.category}</p>
                    ${isUploaded ? '<p class="text-xs mt-1"><i class="fa-solid fa-floppy-disk mr-1"></i> Saved to disk</p>' : ''}
                </div>
            </figure>
        `;
        gallery.appendChild(card);
    });
};