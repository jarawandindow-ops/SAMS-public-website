
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.0";
const supabase=createClient("https://evnhavenxnxodymshwwp.supabase.co","sb_publishable_9THXjlJqCrGrinDeUkEs3A_F-nbugRF",{auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});
const route=location.pathname.split("/").pop().replace(/\.html$/,"")||"index";
const slug=({"index":"home","what-we-do":"what-we-do","get-support":"get-support","get-involved":"get-involved","contact":"contact","about":"about","programs":"programs","privacy":"privacy"})[route];
const card=(tag,cls)=>{const el=document.createElement(tag);el.className=cls;return el;};
function paragraph(parent,text){const p=document.createElement("p");p.textContent=text;parent.appendChild(p);return p;}
async function hydrate(){
 if(slug){
  const {data,error}=await supabase.from("sams_public_pages").select("title,heading,summary,body").eq("slug",slug).maybeSingle();
  if(!error&&data){
   if(route==="index"){
     const h=document.querySelector(".hero h1");
     const lead=document.querySelector(".hero .lead");
     // Keep the organisation's multi-line brand slogan until it is deliberately changed.
     if(h&&data.heading&&data.heading!=="No shame. No judgement. Just mob supporting mob.")h.textContent=data.heading;
     if(lead&&data.summary)lead.textContent=data.summary;
     const purpose=document.querySelector(".section.paper .body-large");
     if(purpose&&data.body)purpose.textContent=data.body;
   }else{
     const h=document.querySelector(".inner-hero h1");
     const para=document.querySelector(".section.paper .prose>p, .section.paper .split>div>p.body-large");
     if(h&&data.heading)h.textContent=data.heading;
     if(para&&data.summary)para.textContent=data.summary;
     const prose=document.querySelector(".section.paper .prose");
     if(prose&&data.body&&["about","what-we-do","privacy"].includes(route)){
       let extra=document.getElementById("sams-approved-copy");
       if(!extra){extra=card("section","notice spaced");extra.id="sams-approved-copy";prose.appendChild(extra);}
       extra.textContent=data.body;
     }
   }
  }
 }
 if(route==="programs"||route==="index"||route==="what-we-do"){
  const {data,error}=await supabase.from("sams_programs").select("name,description,status,sort_order").eq("published",true).order("sort_order",{ascending:true});
  const container=route==="index"?document.querySelector(".sand .card-grid.three"):route==="programs"?document.querySelector(".section.paper .card-grid.three"):null;
  if(container&&!error&&data?.length){
    container.textContent="";
    for(const program of data){
       const item=card("article","service");
       const badge=card("span","pill");badge.textContent=program.status;
       const title=document.createElement("h3");title.textContent=program.name;
       const p=document.createElement("p");p.textContent=program.description;
       item.append(badge,title,p);
       container.append(item);
    }
  }
 }
 if(route==="updates"||route==="index"){
   const {data,error}=await supabase.from("sams_posts").select("title,body,created_at").eq("published",true).order("created_at",{ascending:false}).limit(route==="index"?2:15);
   if(!error&&data?.length){
    const target=route==="updates"?document.querySelector(".section.paper .prose"):null;
    if(target){
      const prior=target.querySelector(".feature.spaced");
      if(prior)prior.remove();
      let list=document.createElement("div");list.id="sams-live-posts";list.className="stack spaced";
      for(const post of data){
       const article=card("article","feature");article.classList.add("spaced");
       const date=card("span","number");date.textContent=new Date(post.created_at).toLocaleDateString("en-AU",{day:"numeric",month:"long",year:"numeric"});
       const h=document.createElement("h3");h.textContent=post.title;
       const body=paragraph(article,post.body);article.prepend(date,h);
       list.append(article);
      }
      target.insertBefore(list,target.querySelector(".notice")||null);
      const note=target.querySelector(".notice");if(note)note.textContent="Only approved announcements are published here.";
    }
   }
 }
}
hydrate().catch(()=>{/* Keep public static content visible during network errors. */});
