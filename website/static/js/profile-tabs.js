document.addEventListener("DOMContentLoaded", function() {
    function activateTab(hash) {
        const tabLink = document.querySelector(`a[href="${hash}"]`);
        if (tabLink) {
            const tabContent = document.querySelector(hash);
            if (tabContent) {
                // Remove active class from all tabs and tab contents
                document.querySelectorAll('#profileTabs a').forEach(tab => tab.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(content => content.classList.remove('show', 'active'));

                // Add active class to the clicked tab and corresponding tab content
                tabLink.classList.add('active');
                tabContent.classList.add('show', 'active');
            }
        }
    }

    // Activate tab based on the hash in the URL
    if (window.location.hash) {
        activateTab(window.location.hash);
    }

    // Add click event listeners to the nav links
    document.querySelectorAll('#profileTabs a').forEach(tabLink => {
        tabLink.addEventListener('click', function(event) {
            event.preventDefault();
            const hash = this.getAttribute('href');
            history.pushState(null, null, hash);
            activateTab(hash);
        });
    });

    // Handle browser back and forward button
    window.addEventListener('hashchange', function() {
        activateTab(window.location.hash);
    });
});
