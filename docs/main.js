function filtertable(){ 
  const tbl = document.getElementById("movietable");
  const trs = tbl.getElementsByTagName("tr");
  const now = new Date();
  //let now = new Date(2021, 2, 26); //for debug purpose
  let tags_to_remove = [];
  for (let i = 0; i < trs.length; i++){
    let elem = trs[i];
    
    // 上映開始日が過去なら上映中にする
    let start_date_tag = elem.getElementsByClassName("start_date")[0];
    let start_date_str = start_date_tag.textContent;
    let start_date = null;
    if (start_date_str) {
      let m = start_date_str.match(/(\d{4})\/(\d{2})\/(\d{2}).*/);
      if (m){
        start_date = new Date(m[1], m[2]-1, m[3]);
        if (start_date <= now) {
          console.log("Now Showing:", elem.textContent);
          start_date_tag.innerText = "上映中";
        }
      }
    }
    
    // 上映終了日が過去なら消す
    let end_date_tag = elem.getElementsByClassName("end_date")[0];
    let end_date_str = end_date_tag.textContent;
    let end_date = null;
    if (end_date_str) {
      let m = end_date_str.match(/(\d{4})\/(\d{2})\/(\d{2})/);
      if (m){
        end_date = new Date(m[1], m[2]-1, m[3], 23, 59, 59, 999);
        //console.log(end_date);
        if (end_date < now) {
          //elem.style.display = "none"; // display: noneではnth-child(odd)セレクタの表示が変になるので消す
          tags_to_remove.push(elem);
          console.log("Removed:", elem.textContent);
        }
      }
    }
  }
  for (let i = 0; tags_to_remove.length > 0; i++){
    tags_to_remove.pop().remove();
  }
}

document.addEventListener('DOMContentLoaded', filtertable);