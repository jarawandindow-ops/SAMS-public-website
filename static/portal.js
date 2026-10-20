
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.0";
const sb = createClient("https://evnhavenxnxodymshwwp.supabase.co", "sb_publishable_9THXjlJqCrGrinDeUkEs3A_F-nbugRF", {auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
const APP=document.getElementById("app");
const ADDRESS="sam.support.admin@gmail.com";
const OWNER_SETUP=new URLSearchParams(location.search).get("setup")==="owner";
let INVITE_TOKEN=new URLSearchParams(location.search).get("invite")||(()=>{
  try{return sessionStorage.getItem("sams_pending_invite");}catch{return null;}
})();
if(INVITE_TOKEN && /^[0-9a-f-]{36}$/i.test(INVITE_TOKEN)){
  try{sessionStorage.setItem("sams_pending_invite",INVITE_TOKEN);}catch{}
}
let person=null,profile=null,view="overview",mfaSetup=null,challengeFactor=null,editing=null,message="",inviteNotice="",granted=new Set();
const E=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const $=sel=>document.querySelector(sel);
const read=(f,n)=>String(new FormData(f).get(n)??"").trim();
const can=(...roles)=>profile?.active===true&&roles.includes(profile.role);
const canUse=permission=>can("owner")||(profile?.active===true&&granted.has(permission));
const fmt=date=>date?new Date(date).toLocaleDateString("en-AU"):"—";
const closeToHome=()=>location.href="index.html";
const status=(text,bad=false)=>{message=text||"";const spot=$("#message-bar");if(spot){spot.innerHTML=message?'<div class="alert '+(bad?'alert-danger':'alert-success')+'">'+E(message)+'</div>':'';}};
const fail=(err)=>{
 console.error(err);
 const message=String(err?.message||"Something went wrong. Please try again.");
 if(/email address not authorized|email not allowed|not authorized to send/i.test(message)){
   status("SAMS account confirmation email isn't available to this address yet. Your account cannot be activated until the organisation's email sender is verified.",true);
 }else if(/redirect.*not allowed|redirect.*not permitted|redirect.*invalid/i.test(message)){
   status("SAMS sign-in email verification needs the website address added to the organisation's authentication settings.",true);
 }else{
   status(message,true);
 }
};
const must=(result)=>{if(result?.error)throw result.error;return result?.data;};
const btn=(label,action,cls="btn")=>'<button type="button" class="'+E(cls)+'" data-action="'+E(action)+'">'+E(label)+'</button>';
const title=(eyebrow,heading,sub,button="")=>'<div class="screen-header"><div><p class="eyebrow">'+E(eyebrow)+'</p><h1>'+E(heading)+'</h1><p>'+E(sub||"")+'</p></div>'+button+'</div>';
const empty=text=>'<div class="empty">'+E(text)+'</div>';
const tabs=[
 ["overview","Overview","All roles"],["pages","Website pages","owner"],["programs","Programs","owner"],["updates","News & updates","owner"],["tasks","Team tasks","team"],["partners","Partnerships","partners"],["team","Staff access","owner"],["audit","Activity log","owner"],["privacy","Privacy & safeguards","team"]
];
const roleLabel={owner:"Owner",admin:"Website administrator",staff:"Staff",intake:"Intake officer",support:"Support worker",peer:"Peer mentor",partnerships:"Partnerships coordinator",pending:"Awaiting approval"};
const allowedTab=t=>t==="overview"||
(t==="pages"&&canUse("website_edit"))||
(t==="programs"&&canUse("programs_manage"))||
(t==="updates"&&canUse("updates_manage"))||
(t==="team"&&can("owner"))||
(t==="tasks"&&can("owner","admin","staff","intake","support","peer","partnerships"))||
(t==="privacy"&&can("owner","admin","staff","intake","support","peer","partnerships"))||
(t==="partners"&&canUse("partners_manage"))||
(t==="audit"&&can("owner"));
function authScreen(mode="login",error=""){
  person=null;profile=null;
  const ownerMode=OWNER_SETUP;
  APP.innerHTML='<section class="auth-panel"><p class="eyebrow">'+(ownerMode?'SAMS · Verified owner setup':'Private SAMS workspace')+'</p><h1>'+(ownerMode?'Set up your SAMS owner account.':'Welcome to SAMS.')+'</h1><p class="intro">'+(ownerMode?'The owner account is reserved for the verified SAMS administration email. Create your own private password, verify the email, and connect Microsoft Authenticator. Owner privileges are issued only after both checks succeed.':'Secure sign-in for SAMS committee members, volunteers and staff. You will also need Microsoft Authenticator on your phone.')+'</p>'
  +(error?'<div class="alert alert-danger">'+E(error)+'</div>':"")
  +'<div id="message-bar"></div>'
  +'<form id="sign-form" class="form" data-form="'+mode+'">'
  +(mode==="signup"?'<label>Full name<input name="full_name" autocomplete="name" required maxlength="100" '+(ownerMode?'value="SAMS Administrator"':'')+'></label>':"")
  +'<label>Email<input type="email" name="email" autocomplete="email" required '+(ownerMode?'readonly value="'+E(ADDRESS)+'"':'')+'></label>'
  +'<label>Password<input type="password" name="password" minlength="12" autocomplete="'+(mode==="signup"?"new-password":"current-password")+'" required></label>'
  +'<button type="submit" class="btn btn-terracotta">'+(mode==="signup"?"Create account":"Sign in securely")+'</button></form>'
  +'<p class="fineprint">'+(ownerMode?'Use a new password you have not shared anywhere else. SAMS will never ask you to send it by email or chat. The owner role is not available until email and six-digit Authenticator verification both pass.':'Every staff account requires verified email and Microsoft Authenticator. Only accounts approved by SAMS can access internal features. If a verification email cannot be sent, contact the SAMS administration inbox; never share a password or authenticator code.')+'</p>'
  +'<div class="row">'+btn(mode==="signup"?"Already have an account? Sign in":(ownerMode?"New owner? Create account":"New worker? Create an account"),"auth-toggle","btn btn-secondary")+'</div>'
  +'<div class="alert">This is a peer-support administration pilot. Do not enter client health histories, case notes or other sensitive information.</div></section>';
  $("#auth-toggle")?.addEventListener("click",()=>{});
}
function authenticationPending(text){
  APP.innerHTML='<section class="auth-panel"><p class="eyebrow">Account verification</p><h1>Check your email.</h1><p>'+E(text)+'</p>'+btn("Return to sign in","back-login")+'</section>';
}
function mfaIntro(){
  APP.innerHTML='<section class="auth-panel"><p class="eyebrow">Required second factor</p><h1>Secure your account.</h1><p>Use the free Microsoft Authenticator app. Add an <strong>Other account</strong> with the QR code. No paid Microsoft subscription is required.</p><div id="message-bar"></div>'+btn("Set up Microsoft Authenticator","mfa-enroll","btn btn-terracotta")+'<div class="alert">The staff dashboard remains locked until you verify an authenticator code.</div>'+btn("Sign out","signout","btn btn-secondary")+'</section>';
}
function mfaChallenge(){
  APP.innerHTML='<section class="auth-panel"><p class="eyebrow">Microsoft Authenticator</p><h1>Enter your six-digit code.</h1><p>Open Microsoft Authenticator and enter the current code for SAMS.</p><div id="message-bar"></div><form class="form" data-form="mfa-challenge"><label>Authenticator code<input name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" required></label><button class="btn btn-terracotta" type="submit">Verify and open workspace</button></form>'+btn("Sign out","signout","btn btn-secondary")+'</section>';
}
function mfaEnrollScreen(data){
  mfaSetup=data;
  const qr=data.totp?.qr_code||"";
  const secret=data.totp?.secret||"";
  const safeQr=/^data:image\/svg\+xml[;,]/i.test(qr)||/^data:image\/png;base64,/i.test(qr)?qr:"";
  APP.innerHTML='<section class="auth-panel"><p class="eyebrow">Set up your second factor</p><h1>Connect Authenticator.</h1><p>In Microsoft Authenticator, select <strong>+</strong>, choose <strong>Other account</strong>, and scan this QR code. Then enter the six-digit code below.</p><div id="mfa-qr"></div><p class="fineprint">If you cannot scan the code, use the setup key below:</p><code class="mfa-secret">'+E(secret)+'</code><div id="message-bar"></div><form class="form" data-form="mfa-enroll"><label>Current six-digit code<input name="code" pattern="[0-9]{6}" inputmode="numeric" maxlength="6" required autocomplete="one-time-code"></label><button class="btn btn-terracotta">Enable Authenticator</button></form><p class="fineprint">Do not share this QR code or setup key. It is used only for enrollment.</p>'+btn("Sign out","signout","btn btn-secondary")+'</section>';
  if(safeQr){const img=document.createElement("img");img.alt="Authenticator setup QR code";img.className="qr";img.src=safeQr;$("#mfa-qr").append(img);}
}
async function refresh(){
 try{
  // getUser() throws AuthSessionMissingError before anyone has signed up.
  // Check for an existing session first so first-time registration is possible.
  const sessionResult=await sb.auth.getSession();
  if(sessionResult.error){
    if(/auth session missing|session missing/i.test(String(sessionResult.error.message||""))){
      authScreen(OWNER_SETUP?"signup":"login");return;
    }
    throw sessionResult.error;
  }
  if(!sessionResult.data?.session){
    authScreen(OWNER_SETUP?"signup":"login");return;
  }
  const u=must(await sb.auth.getUser())?.user;
  if(!u){authScreen(OWNER_SETUP?"signup":"login");return;}
  person=u;
  const level=must(await sb.auth.mfa.getAuthenticatorAssuranceLevel());
  if(level.currentLevel!=="aal2"){
   const list=must(await sb.auth.mfa.listFactors());
   challengeFactor=(list.totp||[]).find(f=>f.status==="verified")||(list.totp||[])[0];
   if(challengeFactor)mfaChallenge();else mfaIntro();
   return;
  }
  if(person.email?.toLowerCase()===ADDRESS){
   const current=await sb.from("sams_member_profiles").select("role").eq("user_id",person.id).maybeSingle();
   if(!current.error&&current.data?.role==="pending"){
     const grant=await sb.rpc("sams_claim_owner");
     if(grant.error){console.warn("Verified account requires role review",grant.error.message);message="Owner permission not yet active. Check that the email is verified and your Authenticator code was accepted.";}
   }
  }
  if(INVITE_TOKEN&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(INVITE_TOKEN)){
    const accepted=await sb.rpc("sams_redeem_invitation",{p_invitation:INVITE_TOKEN});
    if(accepted.error){inviteNotice="Invitation could not be activated: "+accepted.error.message;}
    else{
      inviteNotice="Your invitation has been accepted and the chosen SAMS role is now active.";
      INVITE_TOKEN=null;
      try{sessionStorage.removeItem("sams_pending_invite")}catch{}
      try{
       const next=new URL(location.href);next.searchParams.delete("invite");
       history.replaceState(null,"",next.pathname+next.search+next.hash);
      }catch{}
    }
  }
  const info=must(await sb.from("sams_member_profiles").select("*").eq("user_id",person.id).maybeSingle());
  profile=info;
  const resultGrants=await sb.from("sams_permission_grants").select("permission").eq("user_id",person.id);
  granted=new Set(resultGrants.error?[]:(resultGrants.data||[]).map(x=>x.permission));
  if(!profile){
    APP.innerHTML='<section class="auth-panel"><h1>Account approval pending.</h1><p>Your account exists but the SAMS team profile is not yet available. Please sign in again after a few minutes.</p>'+btn("Sign out","signout")+'</section>';
    return;
  }
  if(!profile.active){
    APP.innerHTML='<section class="auth-panel"><h1>Account disabled.</h1><p>This account is currently disabled. Contact SAMS administration if you believe this is an error.</p>'+btn("Sign out","signout")+'</section>';
    return;
  }
  if(!allowedTab(view))view="overview";
  await draw();
 }catch(err){
  console.error(err);
  if(/auth session missing|session missing/i.test(String(err?.message||""))){
    authScreen(OWNER_SETUP?"signup":"login");return;
  }
  authScreen(OWNER_SETUP?"signup":"login","Unable to complete secure sign-in: "+(err.message||"Try again."));
 }
}
async function doLogin(form,signup=false){
 const email=read(form,"email").toLowerCase(),password=read(form,"password");
 if(signup){
  const full_name=read(form,"full_name");
  if(full_name.length<2)throw new Error("Enter your name.");
  const r=await sb.auth.signUp({email,password,options:{data:{full_name},emailRedirectTo:location.origin+"/portal.html"}});
  must(r);
  if(!r.data.session){authenticationPending("Please use the verification link sent to "+email+". Then return here to sign in and connect Authenticator.");return;}
 }else{
  must(await sb.auth.signInWithPassword({email,password}));
 }
 await refresh();
}
async function startMfa(){
 try{
  const data=must(await sb.auth.mfa.enroll({factorType:"totp",friendlyName:"SAMS Microsoft Authenticator"}));
  mfaEnrollScreen(data);
 }catch(err){fail(err);}
}
async function confirmFactor(code,firstTime=false){
 if(!/^\d{6}$/.test(code))throw new Error("Enter a six-digit code.");
 const factorId=firstTime?mfaSetup?.id:challengeFactor?.id;
 if(!factorId)throw new Error("No authenticator factor found. Sign in again.");
 const challenge=must(await sb.auth.mfa.challenge({factorId}));
 must(await sb.auth.mfa.verify({factorId,challengeId:challenge.id,code}));
 mfaSetup=null;challengeFactor=null;await refresh();
}
function frame(){
 let choices=tabs.filter(([v])=>allowedTab(v));
 const names=choices.map(([v,n])=>'<button class="'+(view===v?'active':'')+'" data-view="'+E(v)+'" type="button">'+E(n)+'</button>').join("");
 APP.innerHTML='<div class="sidebar-layout"><aside class="sidebar"><h2>SAMS Staff Portal</h2><p><strong>'+E(profile.display_name||person.email)+'</strong><br><span class="badge badge-teal">'+E(roleLabel[profile.role]||profile.role)+'</span></p><div class="menu-buttons">'+names+'</div><button class="signout" data-action="signout">Sign out ↗</button></aside><div class="workspace-main"><div id="message-bar"></div><section id="workspace-content"><p class="loading">Loading…</p></section></div></div>';
}
const panel=html=>{$("#workspace-content").innerHTML=html;};
async function draw(){
 frame();
 try{
 if(view==="overview")await overview();
 if(view==="pages")await pages();
 if(view==="programs")await programs();
 if(view==="updates")await updates();
 if(view==="tasks")await tasks();
 if(view==="partners")await partners();
 if(view==="team")await team();
 if(view==="audit")await audit();
 if(view==="privacy")await privacy();
 }catch(err){fail(err);panel(empty("The section could not be loaded. Try again shortly."));}
}
async function overview(){
 const active=profile.role!=="pending";
 panel(title("SAMS INTERNAL WORKSPACE","Wominjeka, "+(profile.display_name||"welcome").split(" ")[0]+".","Your role: "+(roleLabel[profile.role]||profile.role))+(inviteNotice?'<div class="alert '+(inviteNotice.startsWith("Invitation could")?'alert-danger':'alert-success')+'">'+E(inviteNotice)+'</div>':'')
 +'<div class="stats"><div class="stat"><strong>01</strong><span>Connected community</span></div><div class="stat"><strong>24/7</strong><span>13YARN available for crisis support</span></div><div class="stat"><strong>0</strong><span>Client files held in this pilot</span></div></div>'
 +(active?'<div class="panel"><h3>Your team workspace</h3><p>SAMS provides peer connection and service navigation. Choose a section from the menu to manage information appropriate to your position. This platform does not provide treatment or clinical advice.</p><div class="actions">'+(canUse("website_edit")?btn("Edit website","go-pages","btn"):'')+btn("View team tasks","go-tasks","btn btn-secondary")+'</div></div>':'<div class="notice"><strong>Awaiting SAMS approval.</strong> You have securely verified your account using Microsoft Authenticator. Your organisation must assign you a role before you can see internal sections.</div>')
 +'<div class="notice"><strong>Private client records are disabled.</strong> Do not enter substance-use histories, family details, medical information, or case notes into tasks, partner contacts, or website content. For urgent needs call 000, 13YARN on 13 92 76, or DirectLine on 1800 888 236.</div>');
}
async function pages(){
 if(!canUse("website_edit"))return;
 const data=must(await sb.from("sams_public_pages").select("*").order("slug"));
 if(editing?.section==="pages"){
  const item=data.find(x=>x.slug===editing.id);
  if(!item){editing=null;return pages();}
  panel(title("CONTENT MANAGEMENT","Edit "+item.title,"Changes appear on the public website after saving.",btn("All pages","back-pages","btn btn-secondary"))
  +'<div class="panel"><form class="form" data-form="save-page" data-id="'+E(item.slug)+'"><label>Page title<input name="title" maxlength="120" required value="'+E(item.title)+'"></label><label>Heading<input name="heading" maxlength="220" required value="'+E(item.heading)+'"></label><label>Short introduction<textarea name="summary" maxlength="600">'+E(item.summary)+'</textarea></label><label>Page information<textarea name="body" maxlength="3500" rows="9">'+E(item.body)+'</textarea></label><div class="actions"><button class="btn btn-terracotta">Save page changes</button>'+btn("Cancel","back-pages","btn btn-secondary")+'</div></form></div>');
  return;
 }
 panel(title("NO-CODE WEBSITE EDITOR","Website pages","Edit the written content on SAMS's public pages.")
 +'<div class="stack">'+data.map(x=>'<article class="entry"><div><h3>'+E(x.title)+'</h3><p>'+E(x.heading)+'</p><small>Updated '+fmt(x.updated_at)+'</small></div><div>'+btn("Edit page","edit-page:"+x.slug,"btn btn-secondary btn-small")+'</div></article>').join("")+'</div>');
}
const progOptions=["In development","Open","Paused","Completed"];
async function programs(){
 if(!canUse("programs_manage"))return;
 const list=must(await sb.from("sams_programs").select("*").order("sort_order"));
 if(editing?.section==="programs"){
  const item=editing.id?list.find(x=>String(x.id)===String(editing.id)):null;
  const v=item||{name:"",description:"",status:"In development",published:false,sort_order:99};
  panel(title("PROGRAM MANAGEMENT",item?"Edit program":"Add program","Only approved programs should be marked Open.",btn("All programs","back-programs","btn btn-secondary"))
   +'<div class="panel"><form class="form" data-form="save-program" data-id="'+E(item?.id||"")+'"><label>Program name<input name="name" maxlength="180" required value="'+E(v.name)+'"></label><label>Plain-language description<textarea name="description" maxlength="1500" rows="5" required>'+E(v.description)+'</textarea></label><div class="form-row"><label>Availability<select name="status">'+progOptions.map(s=>'<option '+(s===v.status?'selected':'')+'>'+E(s)+'</option>').join("")+'</select></label><label>Display order<input name="sort_order" type="number" min="0" max="999" value="'+Number(v.sort_order||0)+'"></label></div><label><input type="checkbox" name="published" '+(v.published?"checked":"")+'> Show on public website</label><button class="btn btn-terracotta">Save program</button></form></div>');return;
 }
 panel(title("SERVICE AND PROGRAM EDITOR","Programs","Advertise services as active only when SAMS has confirmed their availability.",btn("Add program","new-program","btn btn-terracotta"))
 +'<div class="stack">'+list.map(x=>'<article class="entry"><div><span class="badge">'+E(x.status)+'</span><h3>'+E(x.name)+'</h3><p>'+E(x.description)+'</p><small>'+ (x.published?"Publicly visible":"Not published")+'</small></div><div>'+btn("Edit","edit-program:"+x.id,"btn btn-secondary btn-small")+'</div></article>').join("")+'</div>');
}
async function updates(){
 if(!canUse("updates_manage"))return;
 const list=must(await sb.from("sams_posts").select("*").order("created_at",{ascending:false}));
 if(editing?.section==="updates"){
 const item=editing.id?list.find(x=>String(x.id)===String(editing.id)):null;
 const v=item||{title:"",body:"",published:false};
 panel(title("ORGANISATION ANNOUNCEMENTS",item?"Edit announcement":"New announcement","Publish approved, non-confidential updates.",btn("All updates","back-updates","btn btn-secondary"))
 +'<div class="panel"><form class="form" data-form="save-post" data-id="'+E(item?.id||"")+'"><label>Headline<input name="title" maxlength="200" required value="'+E(v.title)+'"></label><label>Announcement<textarea name="body" maxlength="6000" required rows="8">'+E(v.body)+'</textarea></label><label><input type="checkbox" name="published" '+(v.published?"checked":"")+'> Publish on SAMS website</label><button class="btn btn-terracotta">Save announcement</button></form></div>');return;
 }
 panel(title("WEBSITE NEWS","Updates & news","Announcements will appear on the public Updates page.",btn("New announcement","new-post","btn btn-terracotta"))
 +'<div class="stack">'+(list.length?list.map(x=>'<article class="entry"><div><span class="badge">'+(x.published?"Published":"Draft")+'</span><h3>'+E(x.title)+'</h3><p>'+E(x.body).slice(0,350)+'</p><small>'+fmt(x.created_at)+'</small></div>'+btn("Edit","edit-post:"+x.id,"btn btn-secondary btn-small")+'</article>').join(""):empty("No announcements yet."))+'</div>');
}
async function tasks(){
 if(!allowedTab("tasks"))return;
 const list=must(await sb.from("sams_staff_tasks").select("*").order("created_at",{ascending:false}));
 const canCreate=can("owner","admin");
 let staff=[];
 if(canCreate){staff=must(await sb.from("sams_member_profiles").select("user_id,display_name,role").eq("active",true).neq("role","pending"));}
 panel(title("INTERNAL TEAM COORDINATION","Team tasks","General operational tasks only. Do not record private client details.")
 +(canCreate?'<div class="panel"><h3>Create a team task</h3><form data-form="new-task" class="form"><label>Task description<input maxlength="160" name="title" required placeholder="e.g. Prepare program venue checklist"></label><label>Assigned to<select name="assigned_to" required><option value="">Choose a worker</option>'+staff.map(x=>'<option value="'+E(x.user_id)+'">'+E(x.display_name||x.user_id)+" — "+E(roleLabel[x.role]||x.role)+'</option>').join("")+'</select></label><label>Due date (optional)<input type="date" name="due_date"></label><button class="btn">Assign task</button></form></div>':"")
 +'<div class="panel"><h3>Current tasks</h3>'+(list.length?'<div class="stack">'+list.map(x=>'<div class="entry"><div><strong>'+E(x.title)+'</strong><br><span class="badge">'+E(x.status)+'</span> <small>Due '+E(x.due_date||"not set")+'</small></div><div class="actions">'+(x.status!=="Completed"?btn("Mark complete","complete-task:"+x.id,"btn btn-small"):"")+'</div></div>').join("")+'</div>':empty("No tasks assigned yet."))+'</div>');
}
async function partners(){
 if(!allowedTab("partners"))return;
 const list=must(await sb.from("sams_partner_contacts").select("*").order("organisation"));
 panel(title("SERVICE CONNECTIONS","Partnerships","Manage organisational relationships. Do not enter client information.")
 +'<div class="panel"><h3>Add an organisation</h3><form data-form="new-partner" class="form"><label>Organisation name<input name="organisation" maxlength="180" required></label><div class="form-row"><label>Contact person<input name="contact_name" maxlength="120"></label><label>General email<input name="general_email" type="email" maxlength="200"></label></div><label>Phone<input name="public_phone" maxlength="60"></label><label>Notes (organisation details only)<textarea name="notes" maxlength="1200"></textarea></label><button class="btn">Save organisation</button></form></div>'
 +'<div class="panel"><h3>Organisational contacts</h3>'+(list.length?'<div class="stack">'+list.map(x=>'<div class="entry"><div><h3>'+E(x.organisation)+'</h3><p>'+E(x.contact_name)+' · '+E(x.general_email)+' · '+E(x.public_phone)+'</p><small>'+E(x.notes)+'</small></div>'+btn("Remove","delete-partner:"+x.id,"btn btn-danger btn-small")+'</div>').join("")+'</div>':empty("No organisational contacts yet."))+'</div>');
}
async function team(){
 if(!can("owner"))return;
 panel(title("STAFF MANAGEMENT","Manage SAMS staff","Create individual staff invitations, choose account types, roles and detailed permissions.")
  +'<div class="panel"><h3>Invite people and manage their access</h3><p>You can choose what work each person is allowed to do. The confidential client-file functions remain locked until that system is approved.</p><a class="btn btn-terracotta" href="staff-management.html">Manage staff accounts and invitations ↗</a></div>'
  +'<div class="notice">Workers must register with their invited, verified email address and set up Microsoft Authenticator before their permissions become active. No passwords are sent in invitation links.</div>');
}
async function audit(){
 if(!can("owner"))return;
 const events=must(await sb.rpc("sams_recent_audit_events"));
 const names={sams_member_profiles:"Staff account",sams_public_pages:"Website page",sams_programs:"Program",sams_posts:"Announcement",sams_staff_tasks:"Team task",sams_partner_contacts:"Organisation contact"};
 panel(title("ADMINISTRATION OVERSIGHT","Activity log","The latest 100 recorded changes to organisational content and staff roles. Client records are never included.")
  +'<div class="notice"><strong>Privacy by design:</strong> the activity log records which administrative record changed and when. It does not include message text, participant details or health information.</div>'
  +'<div class="table-wrap"><table><thead><tr><th>When</th><th>Area</th><th>Action</th><th>Reference</th><th>Staff role</th></tr></thead><tbody>'
  +(events.length?events.map(e=>'<tr><td>'+E(new Date(e.event_time).toLocaleString("en-AU"))+'</td><td>'+E(names[e.table_name]||e.table_name)+'</td><td>'+E(e.operation)+'</td><td>'+E(e.record_reference||"—")+'</td><td>'+E(e.actor_role||"System")+'</td></tr>').join(""):'<tr><td colspan="5">No changes have been recorded yet.</td></tr>')
  +'</tbody></table></div>');
}
async function privacy(){
 panel(title("PEER SUPPORT, NOT CLINICAL TREATMENT","Privacy and safeguards","The SAMS pilot separates operational work from confidential records.")
 +'<div class="stats"><div class="stat"><strong>2FA</strong><span>Authenticator required</span></div><div class="stat"><strong>RLS</strong><span>Database access controls</span></div><div class="stat"><strong>OFF</strong><span>Client case records</span></div></div>'
 +'<div class="panel"><h3>What this workspace is for</h3><p>Managing SAMS web copy, planned activities, staff roles, organisational contacts and ordinary staff tasks. These are not treatment or client case-management records.</p><h3>What must not be entered</h3><p>Substance-use history, diagnoses, medical notes, family and child-protection circumstances, clinical counselling records, full intake forms, personal identifiers, or confidential stories shared by participants.</p><h3>Public enquiry email</h3><p>General administrative contact: <a href="mailto:'+ADDRESS+'">'+ADDRESS+'</a>. Online submissions are intentionally disabled until an approved secure email delivery service and privacy collection notice are configured.</p><h3>Before real client records can be activated</h3><p>Documented privacy approval, independent security testing, incident response, retention and deletion schedule, tested backups and a secure referral/consent process must be completed.</p></div>');
}
async function action(name){
 try{
 if(name==="auth-toggle"){authScreen($("#sign-form")?.dataset.form==="signup"?"login":"signup");return;}
 if(name==="back-login"){authScreen();return;}
 if(name==="signout"){await sb.auth.signOut();person=null;profile=null;view="overview";authScreen();return;}
 if(name==="mfa-enroll"){await startMfa();return;}
 if(name==="go-pages"){view="pages";editing=null;await draw();return;}
 if(name==="go-tasks"){view="tasks";editing=null;await draw();return;}
 if(name.startsWith("edit-page:")){editing={section:"pages",id:name.slice(10)};await pages();return;}
 if(name==="back-pages"){editing=null;await pages();return;}
 if(name==="new-program"){editing={section:"programs",id:null};await programs();return;}
 if(name.startsWith("edit-program:")){editing={section:"programs",id:name.slice(13)};await programs();return;}
 if(name==="back-programs"){editing=null;await programs();return;}
 if(name==="new-post"){editing={section:"updates",id:null};await updates();return;}
 if(name.startsWith("edit-post:")){editing={section:"updates",id:name.slice(10)};await updates();return;}
 if(name==="back-updates"){editing=null;await updates();return;}
 if(name.startsWith("complete-task:")){
   const id=Number(name.slice(14));
   must(await sb.from("sams_staff_tasks").update({status:"Completed"}).eq("id",id));
   await tasks();status("Task marked complete.");return;
 }
 if(name.startsWith("delete-partner:")){
   if(!confirm("Remove this organisational contact?"))return;
   must(await sb.from("sams_partner_contacts").delete().eq("id",Number(name.slice(15))));
   await partners();status("Organisational contact removed.");return;
 }
 }catch(err){fail(err);}
}
async function submitted(form){
 let kind=form.dataset.form,button=form.querySelector("[type=submit]");
 if(button)button.disabled=true;
 try{
 if(kind==="login"||kind==="signup"){await doLogin(form,kind==="signup");return;}
 if(kind==="mfa-enroll"||kind==="mfa-challenge"){await confirmFactor(read(form,"code"),kind==="mfa-enroll");return;}
 if(!person||!profile||!profile.active)throw Error("Sign in first.");
 if(kind==="save-page"){
  if(!canUse("website_edit"))throw Error("Not authorised.");
  must(await sb.from("sams_public_pages").update({title:read(form,"title"),heading:read(form,"heading"),summary:read(form,"summary"),body:read(form,"body"),updated_at:new Date().toISOString()}).eq("slug",form.dataset.id));
  editing=null;await pages();status("Page saved. Public website content will update for visitors when they reload.");return;
 }
 if(kind==="save-program"){
  if(!canUse("programs_manage"))throw Error("Not authorised.");
  const data={name:read(form,"name"),description:read(form,"description"),status:read(form,"status"),published:new FormData(form).has("published"),sort_order:Number(read(form,"sort_order"))||0};
  if(form.dataset.id)must(await sb.from("sams_programs").update(data).eq("id",Number(form.dataset.id)));
  else must(await sb.from("sams_programs").insert(data));
  editing=null;await programs();status("Program details saved.");return;
 }
 if(kind==="save-post"){
  if(!canUse("updates_manage"))throw Error("Not authorised.");
  const data={title:read(form,"title"),body:read(form,"body"),published:new FormData(form).has("published")};
  if(form.dataset.id)must(await sb.from("sams_posts").update(data).eq("id",Number(form.dataset.id)));
  else must(await sb.from("sams_posts").insert(data));
  editing=null;await updates();status("Announcement saved.");return;
 }
 if(kind==="new-task"){
  if(!canUse("team_tasks_manage"))throw Error("Not authorised.");
  must(await sb.from("sams_staff_tasks").insert({title:read(form,"title"),assigned_to:read(form,"assigned_to"),due_date:read(form,"due_date")||null,created_by:person.id}));
  await tasks();status("Task assigned.");return;
 }
 if(kind==="new-partner"){
  if(!canUse("partners_manage"))throw Error("Not authorised.");
  const data={organisation:read(form,"organisation"),contact_name:read(form,"contact_name"),general_email:read(form,"general_email"),public_phone:read(form,"public_phone"),notes:read(form,"notes")};
  must(await sb.from("sams_partner_contacts").insert(data));
  await partners();status("Organisational contact saved.");return;
 }
 if(kind==="member-access"){
  if(!can("owner"))throw Error("Only owners can change roles.");
  must(await sb.rpc("sams_manage_member",{target:form.dataset.id,new_role:read(form,"role"),new_active:new FormData(form).has("active")}));
  await team();status("Staff permissions updated.");return;
 }
 }catch(err){fail(err);}
 finally{if(button&&button.isConnected)button.disabled=false;}
}
APP.addEventListener("click",async event=>{
 const a=event.target.closest("[data-action]");
 if(a){event.preventDefault();await action(a.dataset.action);return;}
 const b=event.target.closest("[data-view]");
 if(b){event.preventDefault();if(allowedTab(b.dataset.view)){view=b.dataset.view;editing=null;await draw();}return;}
});
APP.addEventListener("submit",async event=>{
 const form=event.target.closest("form[data-form]");
 if(form){event.preventDefault();await submitted(form);}
});
sb.auth.onAuthStateChange((event)=>{
 if(event==="SIGNED_OUT"){person=null;profile=null;view="overview";authScreen();}
});
refresh();
