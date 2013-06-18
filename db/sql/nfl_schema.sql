/* NFL TEAMS */
CREATE TABLE nfl (
    team TEXT PRIMARY KEY,
    eid INTEGER,
    roto TEXT,
    full TEXT,
    draft TEXT,
    yahoo TEXT,
    short TEXT,
    conf TEXT,
    div TEXT,
    st TEXT,
    spotrac TEXT,
    nid INTEGER,
    pfrshort TEXT,
    pfrurl TEXT,
    dh TEXT
);
/* NFL TEAMS. ONE ENTRY PER TEAM.*/
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('ARI','22','Arizona Cardinals','arz','ari','Arizona','Cardinals','nfc','west','arizona1','arizona-cardinals','3800','ari','crd','cardinals');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('ATL','1','Atlanta Falcons','atl','atl','Atlanta','Falcons','nfc','south','atlanta','atlanta-falcons','0200','atl','atl','falcons');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('BAL','33','Baltimore Ravens','bal','bal','Baltimore','Ravens','afc','north','baltimore','baltimore-ravens','0325','bal','rav','ravens');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('BUF','2','Buffalo Bills','buf','buf','Buffalo','Bills','afc','east','buffalo','buffalo-bills','0610','buf','buf','bills');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('CAR','29','Carolina Panthers','car','car','Carolina','Panthers','nfc','south','carolina','carolina-panthers','0750','car','car','panthers');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('CHI','3','Chicago Bears','chi','chi','Chicago','Bears','nfc','north','chicago','chicago-bears','0810','chi','chi','bears');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('CIN','4','Cincinnati Bengals','cin','cin','Cincinnati','Bengals','afc','north','cincinnati','cincinnati-bengals','0920','cin','cin','bengals');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('CLE','5','Cleveland Browns','cle','cle','Cleveland','Browns','afc','north','cleveland','cleveland-browns','1050','cle','cle','browns');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('DAL','6','Dallas Cowboys','dal','dal','Dallas','Cowboys','nfc','east','dallas','dallas-cowboys','1200','dal','dal','cowboys');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('DEN','7','Denver Broncos','den','den','Denver','Broncos','afc','west','denver','denver-broncos','1400','den','den','broncos');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('DET','8','Detroit Lions','det','det','Detroit','Lions','nfc','north','detroit','detroit-lions','1540','det','det','lions');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('GB','9','Green Bay Packers','gb','gnb','Green Bay','Packers','nfc','north','greenbay','green-bay-packers','1800','gnb','gnb','packers');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('HOU','34','Houston Texans','hou','hou','Houston','Texans','afc','south','houston','houston-texans','2120','hou','htx','texans');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('IND','11','Indianapolis Colts','ind','ind','Indianapolis','Colts','afc','south','indianapolis','indianapolis-colts','2200','ind','clt','colts');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('JAC','30','Jacksonville Jaguars','jac','jac','Jacksonville','Jaguars','afc','south','jacksonville','jacksonville-jaguars','2250','jax','jax','jaguars');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('KC','12','Kansas City Chiefs','kc','kan','Kansas City','Chiefs','afc','west','kansascity','kansas-city-chiefs','2310','kan','kan','chiefs');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('MIA','15','Miami Dolphins','mia','mia','Miami','Dolphins','afc','east','miami','miami-dolphins','2700','mia','mia','dolphins');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('MIN','16','Minnesota Vikings','min','min','Minnesota','Vikings','nfc','north','vikings','minnesota-vikings','3000','min','min','vikings');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('NE','17','New England Patriots','ne','nwe','New England','Patriots','afc','east','patriots','new-england-patriots','3200','nwe','nwe','patriots');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('NO','18','New Orleans Saints','no','nor','New Orleans','Saints','nfc','south','neworleans','new-orleans-saints','3300','nor','nor','saints');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('NYG','19','New York Giants','nyg','nyg','NY Giants','Giants','nfc','east','nygiants','new-york-giants','3410','nyg','nyg','giants');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('NYJ','20','New York Jets','nyj','nyj','NY Jets','Jets','afc','east','jets','new-york-jets','3430','nyj','nyj','jets');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('OAK','13','Oakland Raiders','oak','oak','Oakland','Raiders','afc','west','oakland','oakland-raiders','2520','oak','rai','raiders');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('PHI','21','Philadelphia Eagles','phi','phi','Philadelphia','Eagles','nfc','east','eagles1','philadelphia-eagles','3700','phi','phi','eagles');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('PIT','23','Pittsburgh Steelers','pit','pit','Pittsburgh','Steelers','afc','north','Pittsburgh-Steelers-logo-psd22874','pittsburgh-steelers','3900','pit','pit','steelers');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('SD','24','San Diego Chargers','sd','sdg','San Diego','Chargers','afc','west','chargers2','san-diego-chargers','4400','sdg','sdg','chargers');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('SF','25','San Francisco 49ers','sf','sfo','San Francisco','49ers','nfc','west','49ers1','san-francisco-49ers','4500','sfo','sfo','49ers');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('SEA','26','Seattle Seahawks','sea','sea','Seattle','Seahawks','nfc','west','hawks3','seattle-seahawks','4600','sea','sea','seahawks');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('STL','14','St. Louis Rams','stl','stl','St. Louis','Rams','nfc','west','rams2s','st.-louis-rams','2510','stl','ram','rams');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('TB','27','Tampa Bay Buccaneers','tb','tam','Tampa Bay','Buccaneers','nfc','south','tampa1','tampa-bay-buccaneers','4900','tam','tam','buccaneers');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('TEN','10','Tennessee Titans','ten','ten','Tennessee','Titans','afc','south','tennessee','tennessee-titans','2100','ten','oti','titans');
INSERT INTO nfl (team,eid,full,roto,yahoo,draft,short,conf,div,st,spotrac,nid,pfrshort,pfrurl,dh) values ('WSH','28','Washington Redskins','was','was','Washington','Redskins','nfc','east','washington','washington-redskins','5110','was','was','redskins');

/* NFL TEAM ALIASES */
CREATE TABLE nflteamaliases (
    team TEXT,
    teamalias TEXT,
    FOREIGN KEY(team) REFERENCES nfl(team)
);
/* EACH ALIAS IS INDIVIDUAL LINE. SOME TEAMS WILL HAVE MORE THAN OTHERS. */
INSERT INTO nflteamaliases (team, teamalias) values ('ARI','arz');
INSERT INTO nflteamaliases (team, teamalias) values ('ARI','arizona');
INSERT INTO nflteamaliases (team, teamalias) values ('ARI','cardinals');
INSERT INTO nflteamaliases (team, teamalias) values ('ATL','atlanta');
INSERT INTO nflteamaliases (team, teamalias) values ('ATL','falcons');
INSERT INTO nflteamaliases (team, teamalias) values ('ATL','dirtybirds');
INSERT INTO nflteamaliases (team, teamalias) values ('BAL','baltimore');
INSERT INTO nflteamaliases (team, teamalias) values ('BAL','ravens');
INSERT INTO nflteamaliases (team, teamalias) values ('BUF','buffalo');
INSERT INTO nflteamaliases (team, teamalias) values ('BUF','bills');
INSERT INTO nflteamaliases (team, teamalias) values ('CAR','carolina');
INSERT INTO nflteamaliases (team, teamalias) values ('CAR','panthers');
INSERT INTO nflteamaliases (team, teamalias) values ('CHI','chicago');
INSERT INTO nflteamaliases (team, teamalias) values ('CHI','bears');
INSERT INTO nflteamaliases (team, teamalias) values ('CIN','cincinatti');
INSERT INTO nflteamaliases (team, teamalias) values ('CIN','bengals');
INSERT INTO nflteamaliases (team, teamalias) values ('CIN','bungles');
INSERT INTO nflteamaliases (team, teamalias) values ('CLE','cleveland');
INSERT INTO nflteamaliases (team, teamalias) values ('CLE','browns');
INSERT INTO nflteamaliases (team, teamalias) values ('DAL','dallas');
INSERT INTO nflteamaliases (team, teamalias) values ('DAL','cowboys');
INSERT INTO nflteamaliases (team, teamalias) values ('DAL','cowgirls');
INSERT INTO nflteamaliases (team, teamalias) values ('DEN','denver');
INSERT INTO nflteamaliases (team, teamalias) values ('DEN','broncos');
INSERT INTO nflteamaliases (team, teamalias) values ('DET','detroit');
INSERT INTO nflteamaliases (team, teamalias) values ('DET','lions');
INSERT INTO nflteamaliases (team, teamalias) values ('GB','greenbay');
INSERT INTO nflteamaliases (team, teamalias) values ('GB','packers');
INSERT INTO nflteamaliases (team, teamalias) values ('GB','gbp');
INSERT INTO nflteamaliases (team, teamalias) values ('GB','pack');
INSERT INTO nflteamaliases (team, teamalias) values ('GB','fudgepackers');
INSERT INTO nflteamaliases (team, teamalias) values ('HOU','houston');
INSERT INTO nflteamaliases (team, teamalias) values ('HOU','texans');
INSERT INTO nflteamaliases (team, teamalias) values ('IND','colts');
INSERT INTO nflteamaliases (team, teamalias) values ('JAC','jags');
INSERT INTO nflteamaliases (team, teamalias) values ('JAC','jaguars');
INSERT INTO nflteamaliases (team, teamalias) values ('KC','chiefs');
INSERT INTO nflteamaliases (team, teamalias) values ('MIA','miami');
INSERT INTO nflteamaliases (team, teamalias) values ('MIA','dolphins');
INSERT INTO nflteamaliases (team, teamalias) values ('MIA','fins');
INSERT INTO nflteamaliases (team, teamalias) values ('MIN','vikings');
INSERT INTO nflteamaliases (team, teamalias) values ('NE','nep');
INSERT INTO nflteamaliases (team, teamalias) values ('NE','patriots');
INSERT INTO nflteamaliases (team, teamalias) values ('NE','pats');
INSERT INTO nflteamaliases (team, teamalias) values ('NO','saints');
INSERT INTO nflteamaliases (team, teamalias) values ('NO','aints');
INSERT INTO nflteamaliases (team, teamalias) values ('NYG','giants');
INSERT INTO nflteamaliases (team, teamalias) values ('NYG','gmen');
INSERT INTO nflteamaliases (team, teamalias) values ('NYG','jints');
INSERT INTO nflteamaliases (team, teamalias) values ('NYG','bigblue');
INSERT INTO nflteamaliases (team, teamalias) values ('NYJ','jets');
INSERT INTO nflteamaliases (team, teamalias) values ('NYJ','jest');
INSERT INTO nflteamaliases (team, teamalias) values ('NYJ','ganggreen');
INSERT INTO nflteamaliases (team, teamalias) values ('OAK','oakland');
INSERT INTO nflteamaliases (team, teamalias) values ('OAK','raiders');
INSERT INTO nflteamaliases (team, teamalias) values ('PHI','eagles');
INSERT INTO nflteamaliases (team, teamalias) values ('PHI','eaglols');
INSERT INTO nflteamaliases (team, teamalias) values ('PHI','iggles');
INSERT INTO nflteamaliases (team, teamalias) values ('PIT','steelers');
INSERT INTO nflteamaliases (team, teamalias) values ('PIT','stoolers');
INSERT INTO nflteamaliases (team, teamalias) values ('SD','sdc');
INSERT INTO nflteamaliases (team, teamalias) values ('SD','bolts');
INSERT INTO nflteamaliases (team, teamalias) values ('SD','chargers');
INSERT INTO nflteamaliases (team, teamalias) values ('SD','superchargers');
INSERT INTO nflteamaliases (team, teamalias) values ('SF','49ers');
INSERT INTO nflteamaliases (team, teamalias) values ('SEA','seattle');
INSERT INTO nflteamaliases (team, teamalias) values ('SEA','seachickens');
INSERT INTO nflteamaliases (team, teamalias) values ('SEA','seahawks');
INSERT INTO nflteamaliases (team, teamalias) values ('SEA','seadderall');
INSERT INTO nflteamaliases (team, teamalias) values ('STL','rams');
INSERT INTO nflteamaliases (team, teamalias) values ('STL','lambs');
INSERT INTO nflteamaliases (team, teamalias) values ('TB','buccaneers');
INSERT INTO nflteamaliases (team, teamalias) values ('TB','bucs');
INSERT INTO nflteamaliases (team, teamalias) values ('TEN','titans');
INSERT INTO nflteamaliases (team, teamalias) values ('WSH','was');
INSERT INTO nflteamaliases (team, teamalias) values ('WSH','redskins');
INSERT INTO nflteamaliases (team, teamalias) values ('WSH','skins');
