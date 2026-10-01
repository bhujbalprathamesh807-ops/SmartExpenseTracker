setTimeout(()=>document.querySelectorAll(".flash").forEach(x=>x.remove()),4000);
document.querySelectorAll("input,select,textarea").forEach(el=>{if(!el.classList.contains("form-control"))el.classList.add("form-control")});
