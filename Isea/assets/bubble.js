export async function render({ model, el }) {
    const mod = await import("https://esm.sh/d3@7");
    const d3 = mod.default ?? mod;
    el.classList.add("isea-card");
    el.style.overflow = "hidden";
    
    const container = document.createElement("div");
    el.appendChild(container);

    // Tooltip
    const tooltip = document.createElement("div");
    tooltip.style.cssText = `
        position: absolute; background: rgba(0,0,0,0.8); color: white; 
        padding: 8px; border-radius: 4px; pointer-events: none; 
        font-size: 12px; opacity: 0; z-index: 100; border: 1px solid #555;
    `;
    document.body.appendChild(tooltip);

    function draw() {
        const data = model.get("data");
        const opts = model.get("options");
        
        container.innerHTML = "";
        
        if (!data || data.length === 0) {
            container.innerHTML = `<div style="padding:20px; color:#888">No data for bubbles</div>`;
            return;
        }

        const width = opts.width || 700;
        const height = opts.height || 500;
        const margin = opts.margin || { top: 50, right: 50, bottom: 50, left: 60 };
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

        // Scales
        // Use Log scale if data spans many orders of magnitude (common in EV stats)
        // Checking range to decide, but defaulting to Linear for simplicity unless specified
        const xMax = d3.max(data, d => d.x) || 100;
        const yMax = d3.max(data, d => d.y) || 100;
        const rMax = d3.max(data, d => d.r) || 10;

        const x = d3.scaleLinear().domain([0, xMax * 1.1]).range([0, innerW]);
        const y = d3.scaleLinear().domain([0, yMax * 1.1]).range([innerH, 0]);
        const r = d3.scaleSqrt().domain([0, rMax]).range([4, 25]); // Sqrt for area sizing

        const color = d3.scaleOrdinal(d3.schemeTableau10);

        // Axes
        const xAxis = d3.axisBottom(x).ticks(5).tickFormat(d3.format(".2s"));
        const yAxis = d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2s"));

        g.append("g").attr("transform", `translate(0,${innerH})`)
            .call(xAxis).attr("color", "#9ca3af").select(".domain").remove();
        
        g.append("g").call(yAxis).attr("color", "#9ca3af").select(".domain").remove();

        // Labels
        g.append("text")
            .attr("x", innerW)
            .attr("y", innerH - 5)
            .attr("text-anchor", "end")
            .style("fill", "#6b7280")
            .style("font-size", "11px")
            .text(opts.xLabel);

        g.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 10)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .style("fill", "#6b7280")
            .style("font-size", "11px")
            .text(opts.yLabel);

        // Grid
        g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-innerW).tickFormat("")).style("opacity", 0.1);
        g.append("g").attr("class", "grid").attr("transform", `translate(0,${innerH})`).call(d3.axisBottom(x).tickSize(-innerH).tickFormat("")).style("opacity", 0.1);

        // Bubbles
        g.selectAll("circle")
            .data(data)
            .join("circle")
            .attr("cx", d => x(d.x))
            .attr("cy", d => y(d.y))
            .attr("r", d => r(d.r))
            .style("fill", d => color(d.group))
            .style("opacity", 0.7)
            .style("stroke", "#fff")
            .style("stroke-width", 1)
            .on("mouseover", function(event, d) {
                d3.select(this).style("opacity", 1).style("stroke-width", 2);
                tooltip.style.opacity = 1;
                tooltip.innerHTML = `
                    <strong>${d.id}</strong><br/>
                    ${opts.xLabel}: ${d.x.toLocaleString()}<br/>
                    ${opts.yLabel}: ${d.y.toLocaleString()}<br/>
                    ${opts.zLabel}: ${d.r.toFixed(2)}%<br/>
                    Group: ${d.group}
                `;
                tooltip.style.left = (event.pageX + 10) + "px";
                tooltip.style.top = (event.pageY - 28) + "px";
            })
            .on("mousemove", function(event) {
                tooltip.style.left = (event.pageX + 10) + "px";
                tooltip.style.top = (event.pageY - 28) + "px";
            })
            .on("mouseout", function() {
                d3.select(this).style("opacity", 0.7).style("stroke-width", 1);
                tooltip.style.opacity = 0;
            });
    }

    draw();
    model.on("change:data", draw);
    model.on("change:options", draw);
    
    return () => { if(tooltip.parentNode) tooltip.parentNode.removeChild(tooltip); };
}