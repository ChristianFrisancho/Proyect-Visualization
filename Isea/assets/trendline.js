export async function render({ model, el }) {
    const mod = await import("https://esm.sh/d3@7");
    const d3 = mod.default ?? mod;
    el.classList.add("isea-card");
    el.style.overflow = "hidden";
    
    const container = document.createElement("div");
    container.style.position = "relative";
    el.appendChild(container);

    // Tooltip container (floating box)
    const tooltip = document.createElement("div");
    tooltip.style.cssText = `
        position: absolute;
        background: rgba(17, 24, 39, 0.95);
        border: 1px solid #374151;
        color: #f3f4f6;
        padding: 8px;
        border-radius: 4px;
        pointer-events: none;
        font-size: 12px;
        display: none;
        z-index: 10;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        min-width: 150px;
    `;
    container.appendChild(tooltip);

    // State for toggled series (hidden ones)
    let hiddenSeries = new Set();

    function draw() {
        const rawData = model.get("data");
        const opts = model.get("options");
        
        // Filter out hidden series for scaling, but keep structure
        const data = rawData.map(d => ({
            ...d,
            visible: !hiddenSeries.has(d.id)
        }));

        const visibleData = data.filter(d => d.visible);

        container.innerHTML = "";
        container.appendChild(tooltip); // Re-attach tooltip

        if (!data || data.length === 0) {
            container.innerHTML += `<div style="padding:20px; color:#888">No trend data available</div>`;
            return;
        }

        const width = opts.width || 800;
        const height = opts.height || 400;
        const margin = opts.margin || { top: 50, right: 150, bottom: 50, left: 60 };
        const innerW = width - margin.left - margin.right;
        const innerH = height - margin.top - margin.bottom;

        const svg = d3.select(container).append("svg")
            .attr("width", width)
            .attr("height", height)
            .style("background", "#111827")
            .style("font-family", "sans-serif");

        const g = svg.append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        // Title
        if (opts.title) {
            svg.append("text")
                .attr("x", width / 2)
                .attr("y", margin.top / 2)
                .attr("text-anchor", "middle")
                .style("fill", "#e5e7eb")
                .style("font-weight", "bold")
                .text(opts.title);
        }

        // --- Scales ---
        // Collect all points to determine domains
        let allPoints = [];
        visibleData.forEach(s => {
            allPoints = allPoints.concat(s.history, s.prediction);
        });

        if (allPoints.length === 0 && visibleData.length > 0) {
             // Fallback if visible series have no points
             allPoints = [{x: 2020, y: 0}, {x: 2025, y: 100}];
        }

        const xExtent = d3.extent(allPoints, d => d.x);
        const yMax = d3.max(allPoints, d => d.y) || 100;

        const x = d3.scaleLinear()
            .domain(xExtent)
            .range([0, innerW]);

        const y = d3.scaleLinear()
            .domain([0, yMax * 1.1]) // Add 10% padding
            .range([innerH, 0]);

        const color = d3.scaleOrdinal(d3.schemeTableau10)
            .domain(data.map(d => d.id));

        // --- Axes ---
        const xAxis = d3.axisBottom(x).tickFormat(d3.format("d")); // No commas in years
        const yAxis = d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2s")); // SI prefix (k, M)

        g.append("g")
            .attr("transform", `translate(0,${innerH})`)
            .call(xAxis)
            .attr("color", "#9ca3af")
            .select(".domain").remove();

        g.append("g")
            .call(yAxis)
            .attr("color", "#9ca3af")
            .select(".domain").remove();

        // Gridlines
        g.append("g")
            .attr("class", "grid")
            .call(d3.axisLeft(y).tickSize(-innerW).tickFormat(""))
            .attr("color", "#374151")
            .style("stroke-dasharray", "3,3")
            .style("opacity", 0.3);

        // --- Line Generators ---
        const lineGen = d3.line()
            .x(d => x(d.x))
            .y(d => y(d.y));

        // --- Draw Series ---
        visibleData.forEach(series => {
            const seriesColor = series.color || color(series.id);

            // History Line (Solid)
            g.append("path")
                .datum(series.history)
                .attr("fill", "none")
                .attr("stroke", seriesColor)
                .attr("stroke-width", 2)
                .attr("d", lineGen);

            // Prediction Line (Dashed)
            g.append("path")
                .datum(series.prediction)
                .attr("fill", "none")
                .attr("stroke", seriesColor)
                .attr("stroke-width", 2)
                .attr("stroke-dasharray", "5,5")
                .attr("d", lineGen);

            // Points (History only)
            g.selectAll(`.point-${series.id.replace(/\s+/g, '-')}`)
                .data(series.history)
                .join("circle")
                .attr("cx", d => x(d.x))
                .attr("cy", d => y(d.y))
                .attr("r", 3)
                .attr("fill", seriesColor);
        });

        // --- Legend ---
        const legend = svg.append("g")
            .attr("transform", `translate(${width - margin.right + 20}, ${margin.top})`);

        data.forEach((series, i) => {
            const seriesColor = series.color || color(series.id);
            const isHidden = hiddenSeries.has(series.id);

            const lg = legend.append("g")
                .attr("transform", `translate(0, ${i * 20})`)
                .style("cursor", "pointer")
                .on("click", () => {
                    if (hiddenSeries.has(series.id)) {
                        hiddenSeries.delete(series.id);
                    } else {
                        hiddenSeries.add(series.id);
                    }
                    draw(); // Redraw
                });

            lg.append("rect")
                .attr("width", 12)
                .attr("height", 12)
                .attr("fill", isHidden ? "#444" : seriesColor)
                .attr("stroke", isHidden ? "#666" : "none");

            lg.append("text")
                .attr("x", 18)
                .attr("y", 10)
                .text(series.id)
                .style("font-size", "10px")
                .style("fill", isHidden ? "#666" : "#e5e7eb");
        });

        // --- Interactive Bisector (Hover Line) ---
        const bisect = d3.bisector(d => d.x).left;
        
        // Overlay rect to capture mouse events
        const overlay = g.append("rect")
            .attr("width", innerW)
            .attr("height", innerH)
            .style("fill", "none")
            .style("pointer-events", "all");

        const focusLine = g.append("line")
            .style("stroke", "#6b7280")
            .style("stroke-width", 1)
            .style("stroke-dasharray", "3,3")
            .style("opacity", 0);

        overlay
            .on("mouseover", () => {
                focusLine.style("opacity", 1);
                tooltip.style.display = "block";
            })
            .on("mouseout", () => {
                focusLine.style("opacity", 0);
                tooltip.style.display = "none";
            })
            .on("mousemove", (event) => {
                const [mx] = d3.pointer(event);
                const yearVal = x.invert(mx);
                const year = Math.round(yearVal);
                
                // Snap line to year
                const snapX = x(year);
                focusLine
                    .attr("x1", snapX)
                    .attr("y1", 0)
                    .attr("x2", snapX)
                    .attr("y2", innerH);

                // Build tooltip content
                let html = `<strong>Year: ${year}</strong><br/>`;
                
                // Sort series by value at this year for better readability
                const currentVals = [];
                visibleData.forEach(s => {
                    // Check history
                    let pt = s.history.find(p => p.x === year);
                    let type = " (Hist)";
                    if (!pt) {
                        pt = s.prediction.find(p => p.x === year);
                        type = " (Pred)";
                    }
                    
                    if (pt) {
                        currentVals.push({
                            id: s.id,
                            val: pt.y,
                            color: s.color || color(s.id),
                            type: type
                        });
                    }
                });

                currentVals.sort((a, b) => b.val - a.val);

                currentVals.forEach(item => {
                    html += `
                        <div style="display:flex; align-items:center; margin-top:4px;">
                            <span style="width:8px;height:8px;background:${item.color};margin-right:6px;display:inline-block;"></span>
                            <span style="flex:1">${item.id}</span>
                            <span style="font-weight:bold; margin-left:8px;">${Math.round(item.val).toLocaleString()}</span>
                        </div>
                    `;
                });

                tooltip.innerHTML = html;
                
                // Position tooltip near mouse but keep inside bounds
                const box = container.getBoundingClientRect();
                let left = event.pageX - box.left + 15;
                let top = event.pageY - box.top + 15;
                
                // Simple boundary check
                if (left + 150 > width) left -= 160;
                
                tooltip.style.left = left + "px";
                tooltip.style.top = top + "px";
            });
    }

    draw();
    model.on("change:data", draw);
    model.on("change:options", draw);

    return () => { if(tooltip.parentNode) tooltip.parentNode.removeChild(tooltip); };
}