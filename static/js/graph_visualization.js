// Color scheme for node types (similar to nckh_group_2.py)
const NODE_COLOR_MAP = {
    "User": "#FF7043",
    "JobPosting": "#FFA726",
    "JobRoleCanonical": "#B0BEC5",
    "JobRoleRaw": "#CFD8DC",
    "Company": "#90CAF9",
    "Location": "#81C784",
    "ExperienceBucket": "#F48FB1",
    "SalaryBucket": "#BA68C8",
    "Skill": "#FFD54F",
    "SkillRaw": "#FFEB3B"
};

// Important edges for highlighting (similar to nckh_group_2.py)
const IMPORTANT_EDGES = {
    "MATCHES_JOB": true,
    "SIMILAR_TO": true,
    "HAS_SKILL": true,
    "REQUIRES_SKILL": true,
    "LOCATED_IN": true,
    "POSTED_BY": true,
    "HAS_ROLE_CANONICAL": true
};

document.addEventListener('DOMContentLoaded', () => {
    // Only initialize when graph tab is visible
    const graphTab = document.querySelector('[data-tab="graph"]');
    if (graphTab) {
        graphTab.addEventListener('click', initializeGraph);
    }
});

let graphInitialized = false;
let network = null;

function initGraphTab() {
    const graphTab = document.querySelector('[onclick*="Graph"]');
    if (graphTab) {
        graphTab.addEventListener('click', function () {
            setTimeout(initializeGraph, 100);
        });
    }
}

document.addEventListener('DOMContentLoaded', initGraphTab);

async function initializeGraph(force = false) {
    // Check if force is actually a boolean true (not an event object)
    const shouldForce = force === true;

    if (!shouldForce && graphInitialized && network) {
        return;
    }

    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) {
        console.error('graph-container not found');
        return;
    }

    if (typeof vis === 'undefined') {
        graphContainer.innerHTML = '<div style="padding: 20px; color: red;">Visualization library not loaded. Please refresh the page.</div>';
        return;
    }

    graphContainer.innerHTML = '<div style="padding: 20px;">Loading graph visualization...</div>';

    try {
        const response = await fetch('/graph');

        if (!response.ok) {
            const errorText = await response.text();
            graphContainer.innerHTML = `<div style="padding: 20px; color: red;">Failed to load graph (${response.status}).</div>`;
            return;
        }

        const data = await response.json();

        if (data.error) {
            graphContainer.innerHTML = `<div style="padding: 20px; color: red;">${data.error}</div>`;
            return;
        }

        if (!data.nodes || data.nodes.length === 0) {
            graphContainer.innerHTML = '<div style="padding: 20px;">No graph data available. Please upload a CV first.</div>';
            return;
        }

        console.log(`Rendering graph: ${data.nodes_count} nodes, ${data.links_count} edges`);

        graphContainer.innerHTML = '';

        // Process nodes with enhanced styling
        const visNodes = data.nodes.map(node => {
            const nodeType = node.ntype || "Other";
            const color = NODE_COLOR_MAP[nodeType] || "#E0E0E0";

            // Calculate node size based on type
            let size = 25;
            if (node.id.includes("user")) size = 50;
            if (nodeType === "JobPosting") size = 40;
            if (nodeType === "Skill") size = 28;
            if (nodeType === "Company") size = 32;
            if (nodeType === "Location") size = 28;

            return {
                id: node.id,
                label: node.label,
                title: `${nodeType}: ${node.label}`,
                color: {
                    background: color,
                    border: nodeType === 'User' ? '#d32f2f' : '#2055e9ff',
                    highlight: {
                        background: color,
                        border: '#14f30c'
                    }
                },
                size: size,
                x: node.x * 500,
                y: node.y * 500,
                fixed: { x: true, y: true },
                font: {
                    size: nodeType === 'User' ? 16 : (nodeType === 'JobPosting' ? 13 : 11),
                    color: '#000',
                    multi: false,
                    face: 'Arial'
                },
                borderWidth: nodeType === 'User' ? 4 : 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.25)',
                    size: 12,
                    x: 5,
                    y: 5
                }
            };
        });

        // Process edges with detailed styling
        const visEdges = data.links.map(edge => {
            const isImportant = IMPORTANT_EDGES[edge.rel];
            const rel = edge.rel.replace(/_/g, ' ');

            // Build label with score/prob if available
            let label = '';
            if (edge.rel === 'MATCHES_JOB' || edge.rel === 'SIMILAR_TO') {
                if (edge.score !== null && edge.score !== undefined) {
                    const scoreType = edge.rel === 'MATCHES_JOB' ? 'MATCH' : 'SIMILAR';
                    label = `${scoreType} (${edge.score.toFixed(3)})`;
                }
            } else {
                label = rel;
            }
            // let label = '';

            // CHỈ hiện số cho 2 loại cạnh này
            // if (edge.rel === 'MATCHES_JOB') {
            //     if (edge.score !== null && edge.score !== undefined) {
            //         label = `MATCH (${edge.score.toFixed(3)})`;
            //     }
            // } 
            // else if (edge.rel === 'SIMILAR_TO') {
            //     if (edge.score !== null && edge.score !== undefined) {
            //         label = `SIMILAR (${edge.score.toFixed(3)})`;
            //     }
            // }
            // // CÁC CẠNH CÒN LẠI: CHỈ HIỆN TÊN REL
            // else {
            //     label = rel;
            // }

            // Edge styling based on relationship type
            let color = '#999';
            let width = 1;
            let fontSize = 9;
            let dashes = true;

            if (edge.rel === 'MATCHES_JOB') {
                color = '#000';
                width = 4;
                fontSize = 12;
                dashes = false;
            } else if (edge.rel === 'SIMILAR_TO') {
                color = '#666';
                width = 3;
                fontSize = 11;
                dashes = false;
            } else if (['HAS_SKILL', 'REQUIRES_SKILL', 'POSTED_BY', 'LOCATED_IN', 'HAS_ROLE_CANONICAL'].includes(edge.rel)) {
                color = '#777';
                width = 1.5;
                fontSize = 10;
                dashes = true;
            }

            return {
                from: edge.source,
                to: edge.target,
                label: label,
                title: `${rel}`,
                font: {
                    align: 'middle',
                    size: fontSize,
                    bold: isImportant,
                    color: '#333',
                    face: 'Arial'
                },
                color: {
                    color: color,
                    highlight: '#f00'
                },
                width: width,
                arrows: {
                    to: {
                        enabled: true,
                        scaleFactor: 0.8,
                        type: 'arrow'
                    }
                },
                dashes: dashes,
                smooth: {
                    enabled: true,
                    type: 'continuous',
                    roundness: 0.4
                }
            };
        });

        const nodes = new vis.DataSet(visNodes);
        const edges = new vis.DataSet(visEdges);

        const networkData = { nodes, edges };
        const options = {
            layout: {
                hierarchical: false
            },
            physics: {
                enabled: false,
                stabilization: {
                    iterations: 0
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                zoomView: true,
                dragView: true,
                navigationButtons: true,
                keyboard: true
            },
            nodes: {
                shape: 'dot',
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.2)',
                    size: 10,
                    x: 5,
                    y: 5
                }
            },
            edges: {
                shadow: false,
                font: {
                    strokeWidth: 0,
                    background: {
                        enabled: true,
                        color: '#ffffff'
                    }
                }
            }
        };

        network = new vis.Network(graphContainer, networkData, options);

        graphInitialized = true;
        console.log('Graph visualization initialized successfully');
        console.log(`Total nodes in graph: ${data.total_nodes}, Total edges: ${data.total_edges}`);

    } catch (error) {
        console.error('Graph error:', error);
        graphContainer.innerHTML = `<div style="padding: 20px; color: red;">Error: ${error.message}</div>`;
    }
}
