document.addEventListener('DOMContentLoaded', async () => {
    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) {
        console.error('graph-container element not found.');
        return;
    }
    if (typeof vis === 'undefined') {
        graphContainer.innerHTML = '<p>Visualization library not loaded.</p>';
        return;
    }

    // Ensure container has size and is a div
    graphContainer.style.minHeight = graphContainer.style.minHeight || '600px';
    graphContainer.style.minWidth = graphContainer.style.minWidth || '100%';
    if (graphContainer.tagName.toLowerCase() !== 'div') {
        const div = document.createElement('div');
        div.id = 'graph-container';
        graphContainer.replaceWith(div);
        return; // reload is needed; simplest exit to avoid double-binding
    }

    try {
        const response = await fetch('/graph-visualization');
        const data = await response.json();

        if (data.error) {
            graphContainer.innerHTML = `<p>${data.error}</p>`;
            return;
        }

        const nodes = new vis.DataSet(data.nodes || []);
        const edges = new vis.DataSet(
            (data.edges || []).map(edge => ({
                from: edge.source,
                to: edge.target,
                label: edge.rel,
                font: { align: 'middle' },
                color: edge.rel === 'MATCHES_JOB' ? 'black' : '#cccccc',
                arrows: edge.rel === 'MATCHES_JOB' ? 'to' : ''
            }))
        );

        const networkData = { nodes, edges };
        const options = {
            nodes: {
                shape: 'dot',
                scaling: { min: 10, max: 30 },
                font: { size: 12, face: 'Tahoma' }
            },
            edges: {
                smooth: true,
                arrows: { to: { enabled: true, scaleFactor: 0.5 } }
            },
            physics: { stabilization: true }
        };

        // Delay render until tab is likely visible to avoid svg=null issues
        requestAnimationFrame(() => {
            try {
                const network = new vis.Network(graphContainer, networkData, options);
                if (data.center_node) {
                    network.focus(data.center_node, { scale: 1.5, animation: true });
                }
            } catch (e) {
                graphContainer.innerHTML = `<p>Error rendering graph: ${e.message}</p>`;
            }
        });
    } catch (error) {
        graphContainer.innerHTML = `<p>Error loading graph: ${error.message}</p>`;
    }
});
