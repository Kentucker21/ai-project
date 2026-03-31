place('Portland').
place('Kingston').
place('St.thomas').
place('St.andrew').
place('St.mary').
place('St.Ann').
place('Trelawny').
place('St.James').
place('Hanover').
place('Westmoreland').
place('St.Elizabeth').
place('Manchester').
place('Clarendon').
place('St.Catherine').


%road types-paved,unpaved
%conditions-broken cistern,deep potholes
%status-open or closed

%portland to st thomas
road('Portland','St.thomas',110,'unpaved','deep potholes',90,open).
road('St.thomas','Portland',110,'unpaved','deep potholes',90,open).

%portland to st mary
road('Portland','St.mary',70.1,'paved','broken cistern',90,open).
road('St.mary','Portland',70.1,'paved','broken cistern',90,open).

%st thomas to st andrew
road('St.thomas','St.andrew',51,'unpaved','none',60,open).
road('St.andrew','St.thomas',51,'unpaved','none',60,open).

%st andrew to kingston 
road('St.andrew','Kingston',8.5,'paved','none',30,open).
road('Kingston','St.andrew',8.5,'paved','deep potholes',30,open).

%kingston to st.catherine
road('Kingston','St.Catherine',34.7,'paved','deep potholes',49,open).
road('St.Catherine','Kingston',34.7,'paved','deep potholes',49,open).

%st catherine to clarendon
road('St.Catherine','Clarendon',47.7,'paved','deep potholes',55,open).
road('Clarendon','St.Catherine',47.7,'paved','deep potholes',55,open).



% condition mapping


avoid_condition('broken cistern', 'broken cistern').
avoid_condition('deep potholes', 'deep potholes').
avoid_condition('none', none).



% road cost filter


road_cost(Current, Next, Dist, NewDur, TypeChoice, AvoidOption) :-
    road(Current, Next, Dist, Type, Cond, Dur, open),

    % enforce road type
    Type = TypeChoice,

    % map avoid option
    avoid_condition(AvoidOption, AvoidCond),

    % filtering logic
    ( AvoidCond = none
    ; Cond \= AvoidCond
    ),

    adjust_duration(Cond, Dur, NewDur).



% dijstra adjustment


adjust_duration('deep potholes', Dur, NewDur) :-
    NewDur is Dur + 5.

adjust_duration('broken cistern', Dur, NewDur) :-
    NewDur is Dur + 5.

adjust_duration('none', Dur, Dur).



% dijkstra entry point


dijkstra(Start, End, Path, Distance, Duration, TypeChoice, AvoidOption) :-
    dijkstra_queue([(0, Start, [Start], 0)], End, RevPath, Distance, Duration, TypeChoice, AvoidOption),
    reverse(RevPath, Path).







dijkstra_queue([(Dist, End, Path, Dur) | _], End, Path, Dist, Dur, _, _).

dijkstra_queue([(Dist, Current, Path, PrevDur) | Rest], End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption) :-

    findall(
        (NewDist, Next, [Next | Path], NewDurTotal),
        (
            road_cost(Current, Next, D, DurAdj, TypeChoice, AvoidOption),
            \+ member(Next, Path),
            NewDist is Dist + D,
            NewDurTotal is PrevDur + DurAdj
        ),
        Neighbors
    ),

    append(Rest, Neighbors, TempQueue),
    sort(TempQueue, SortedQueue),

    dijkstra_queue(SortedQueue, End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption).







add5(Newdur):-road(_,_,_,_,Cond,Dur,_),((Cond=='deep potholes';Cond=='broken cistern')->Newdur is Dur+5,nl,
       write('duration is upgraded, new duration is '),write(Newdur) ;Newdur is Dur+0).


findshortest(S,D,C,Dist):-write('enter start'),read(S),nl,write('enter destination: '),read(D),nl,
              write('enter conditions: '),read(C),
               
              road(S,D,Dist,_,C,_,_).
            
    

%add5:-road(_,_,_,pav,cond,Dur,_).

%DEPTH FIRST SEARCH (DFS)
% DFS entry point(With error handling)
dfs(Start, End, Path, Distance, Duration, TypeChoice, AvoidOption) :-
    dfs_search([Start], End, [Start], Path, 0, Distance, 0, Duration, TypeChoice, AvoidOption), !.

dfs(_, _, ['No path found'], 0, 0, _, _).

% DFS search base case: reached destination
dfs_search([End | _], End, Path, Path, Dist, Dist, Dur, Dur, _, _) :- !.

% DFS search recursive case
dfs_search([Current | Rest], End, Visited, Path, AccDist, FinalDist, AccDur, FinalDur, TypeChoice, AvoidOption) :-
    road_cost(Current, Next, D, DurAdj, TypeChoice, AvoidOption),
    \+ member(Next, Visited),
    NewDist is AccDist + D,
    NewDur is AccDur + DurAdj,
    dfs_search([Next | [Current | Rest]], End, [Next | Visited], Path, NewDist, FinalDist, NewDur, FinalDur, TypeChoice, AvoidOption).

% Backtrack if no valid neighbors
dfs_search([_ | Rest], End, Visited, Path, AccDist, FinalDist, AccDur, FinalDur, TypeChoice, AvoidOption) :-
    dfs_search(Rest, End, Visited, Path, AccDist, FinalDist, AccDur, FinalDur, TypeChoice, AvoidOption).
