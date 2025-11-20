export async function render({ model, el }) {
    const mod = await import("https://esm.sh/d3@7");
    const d3 = mod.default ?? mod;

    el.classList.add("isea-card");
    el.style.overflow = "hidden";
    
    const container = document.createElement("div");
    el.appendChild(container);

    const tooltip = document.createElement("div");
    tooltip.style.cssText = `
        position: absolute; 
        background: rgba(0,0,0,0.8); 
        color: white; 
        padding: 5px 10px; 
        border-radius: 4px; 
        pointer-events: none; 
        font-size: 12px; 
        opacity: 0;
        transition: opacity 0.2s;
        z-index: 1000;
        border: 1px solid #444;
    `;
    document.body.appendChild(tooltip);

    function draw() {
        const data = model.get("data");
        const opts = model.get("options");
        
        container.innerHTML = ""; 
        
        if (!data || data.length === 0) {
            container.innerHTML = `<div style="padding:20px; color:#888">No data available</div>`;
            return;
        }

        const width = opts.width || 600;
        const height = opts.height || 400;
        const margin = opts.margin || { top: 40, right: 20, bottom: 100, left: 100 };
        const innerW = width - margin.left - margin.right;
        const innerH = height - margin.top - margin.bottom;

        const svg = d3.select(container).append("svg")
            .attr("width", width)
            .attr("height", height)
            .style("background", "#111827")
            .style("font-family", "sans-serif");

        const g = svg.append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        if (opts.title) {
            svg.append("text")
                .attr("x", width / 2)
                .attr("y", margin.top / 2)
                .attr("text-anchor", "middle")
                .style("fill", "#e5e7eb")
                .style("font-weight", "bold")
                .text(opts.title);
        }

        const xDomain = opts.xDomain || [...new Set(data.map(d => d.col_id))];
        const yDomain = opts.yDomain || [...new Set(data.map(d => d.row_id))];

        const x = d3.scaleBand()
            .range([0, innerW])
            .domain(xDomain)
            .padding(0.05);

        const y = d3.scaleBand()
            .range([0, innerH])
            .domain(yDomain)
            .padding(0.05);

        const values = data.map(d => d.value).filter(v => v !== null);
        const minVal = d3.min(values);
        const maxVal = d3.max(values);
        
        let colorScale;
        if (opts.cmap === 'coolwarm') {
            colorScale = d3.scaleSequential(d3.interpolateRdBu).domain([1, -1]); 
        } else {
            colorScale = d3.scaleSequential(d3.interpolateViridis).domain([minVal, maxVal]);
        }

        g.append("g")
            .attr("transform", `translate(0, ${innerH})`)
            .call(d3.axisBottom(x).tickSize(0))
            .selectAll("text")
            .attr("transform", "translate(-10,0)rotate(-45)")
            .style("text-anchor", "end")
            .style("fill", "#9ca3af");

        g.append("g")
            .call(d3.axisLeft(y).tickSize(0))
            .selectAll("text")
            .style("fill", "#9ca3af");

        g.selectAll(".domain").remove();

        g.selectAll("rect")
            .data(data, d => d.row_id + ":" + d.col_id)
            .join("rect")
            .attr("x", d => x(d.col_id))
            .attr("y", d => y(d.row_id))
            .attr("width", x.bandwidth())
            .attr("height", y.bandwidth())
            .style("fill", d => d.value === null ? "#333" : colorScale(d.value))
            .style("rx", 4)
            .style("ry", 4)
            .on("mouseover", function(event, d) {
                d3.select(this).style("stroke", "white").style("stroke-width", 2);
                tooltip.style.opacity = 1;
                tooltip.innerHTML = `
                    <strong>${d.row_id}</strong> x <strong>${d.col_id}</strong><br/>
                    Value: ${d.value !== null ? d.value.toFixed(2) : "N/A"}
                `;
                tooltip.style.left = (event.pageX + 10) + "px";
                tooltip.style.top = (event.pageY - 28) + "px";
            })
            .on("mousemove", function(event) {
                tooltip.style.left = (event.pageX + 10) + "px";
                tooltip.style.top = (event.pageY - 28) + "px";
            })
            .on("mouseout", function() {
                d3.select(this).style("stroke", "none");
                tooltip.style.opacity = 0;
            });
            
        if (x.bandwidth() > 30 && y.bandwidth() > 20) {
             g.selectAll(".val-text")
                .data(data)
                .join("text")
                .attr("x", d => x(d.col_id) + x.bandwidth()/2)
                .attr("y", d => y(d.row_id) + y.bandwidth()/2)
                .attr("dy", ".35em")
                .attr("text-anchor", "middle")
                .text(d => d.value !== null ? d.value.toFixed(1) : "")
                .style("fill", d => Math.abs(d.value) > 0.5 ? "white" : "black")
                .style("font-size", "10px")
                .style("pointer-events", "none");
        }
    }

    draw();
    model.on("change:data", draw);
    model.on("change:options", draw);
    
    return () => {
        if(tooltip.parentNode) tooltip.parentNode.removeChild(tooltip);
    };
}