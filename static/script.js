document.addEventListener("DOMContentLoaded", function () {
    const searchForm = document.getElementById("searchForm");
    const uploadForm = document.getElementById("uploadForm");
    const searchingGif = document.getElementById("searchingGif");
    const foundGif = document.getElementById("foundGif");

    if (searchForm) {
        searchForm.addEventListener("submit", function () {
            searchingGif.style.display = "block"; // Show Searching GIF
            foundGif.style.display = "none"; // Hide Found GIF
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener("submit", function () {
            searchingGif.style.display = "block"; // Show Searching GIF
            foundGif.style.display = "none"; // Hide Found GIF
        });
    }
});
