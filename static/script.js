document.getElementById('submit_button').addEventListener('click', async function() {
    const sourceRa = JSON.parse(document.getElementById('source_ra').value);
    const targetRa = JSON.parse(document.getElementById('target_ra').value);

    // Create the request object
    const requestData = {
        source: sourceRa,
        target: targetRa
    };

    try {
        // Send POST request to FastAPI endpoint
        const response = await fetch('/check_equivalence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (response.ok) {
            const result = await response.json();
            document.getElementById('output').textContent = JSON.stringify(result, null, 2);
        } else {
            document.getElementById('output').textContent = 'Error: ' + response.statusText;
        }
    } catch (error) {
        document.getElementById('output').textContent = 'Error: ' + error.message;
    }
});
