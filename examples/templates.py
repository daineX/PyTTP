# -*- coding: utf-8 -*-
from pyttp.html import *


css = """
#tabmenue {
  margin-top:0px;
  padding: 3px;
  border-bottom: 1px solid #888; 
}
#tabmenue li {
 border: 1px solid #000;
  display: inline;
/*  padding: 3px 1em;*/
  /*margin-left: 3px;*/
}
#tabmenue li a {
  padding: 3px 1em;
  color:white;
  text-decoration: none;
  background-image: url(menubg.png);
  background-position: 0px 0px;
  background-repeat: repeat-x;
}

#tabmenue li a:hover {
  background-position: 0px -18px;
}

#tabmenue li span#tabmenue_current {
  padding: 3px 1em;
  color:white;
  background-image: url(menubg.png);
  background-position: 0px -18px;
  background-repeat: repeat-x;
}

/*
#tabmenue li span#tabmenue_current:hover {
  background-position: 0px -18px;
}
*/

#full {
  width: 800px;
  margin-left:auto;
  margin-right:auto;
}

#outershell {
  background-color:#777;
  border: 1px solid #000;
  text-align:left;
  width: 800px;
  margin-left: auto;
  margin-right: auto;
/*  padding: 10px;*/
  float:left;
}

#menudiv {
  background-color: #888;
}

#rightbox {
  width: 230px;
  float: left;
  display:block;
  padding: 5px;
}

#innerdiv {
  margin-left: 10px;
  width:540px;
  float: left;  
  display:block;
  padding: 5px;
  background-color: #ccc;
  height: 100%;
}

#headerdiv {
  height: 120px;
  background-color:#ccc;
/*  border: 1px solid #000; */
  display: block;
  overflow: hidden;
}

#footerdiv {
  clear: left;
  text-align: center;
  padding: 5px;
  background-color:#bbb;
}

body {
  background-color: #aaa;
}
"""

def menu(entries=None, current=0, id="menu"):
    
    return \
    ul(id=id)(
        li(span(id=id+"_current")(text)) if counter == current else li(a(href=link)(text)) for counter, (link, text) in enumerate(entries)
    )
    
def lala():
    pass
        
if __name__ == "__main__":
    
    entries = [("/posts", "Posts"),
               ("/comments", "Comments"),
               ("/news", "News")]
               
    src = \
    html(
        title(
            "Template Test"
        ),
        style(type="text/css")(
            css
        ),
        body(
            div(id="full")(
                div(id="outershell")(
                    div(id="headerdiv")(
                        "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis vitae, justo. Nullam dictum felis eu pede mollis pretium. Integer tincidunt. Cras dapibus. Vivamus elementum semper nisi. Aenean vulputate eleifend tellus. Aenean leo ligula, porttitor eu, consequat vitae, eleifend ac, enim. Aliquam lorem ante, dapibus in, viverra quis, feugiat a, tellus. Phasellus viverra nulla ut metus varius laoreet. Quisque rutrum. Aenean imperdiet. Etiam ultricies nisi vel augue. Curabitur ullamcorper ultricies nisi. Nam eget dui. Etiam rhoncus. Maecenas tempus, tellus eget condimentum rhoncus, sem quam semper libero, sit amet adipiscing sem neque sed ipsum. Nam quam nunc, blandit vel, luctus pulvinar, hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. Donec sodales sagittis magna. Sed consequat, leo eget bibendum sodales, augue velit cursus nunc,"
                    ),
                    div(id="menudiv")(
                        menu(entries, current=1, id="tabmenue")
                    ),
                    div(id="innerdiv")(
                        div(id="headingdiv")(
                            h1("This is a heading.")
                        ),
                        "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis vitae, justo. Nullam dictum felis eu pede mollis pretium. Integer tincidunt. Cras dapibus. Vivamus elementum semper nisi. Aenean vulputate eleifend tellus. Aenean leo ligula, porttitor eu, consequat vitae, eleifend ac, enim. Aliquam lorem ante, dapibus in, viverra quis, feugiat a, tellus. Phasellus viverra nulla ut metus varius laoreet. Quisque rutrum. Aenean imperdiet. Etiam ultricies nisi vel augue. Curabitur ullamcorper ultricies nisi. Nam eget dui. Etiam rhoncus. Maecenas tempus, tellus eget condimentum rhoncus, sem quam semper libero, sit amet adipiscing sem neque sed ipsum. Nam quam nunc, blandit vel, luctus pulvinar, hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. Donec sodales sagittis magna. Sed consequat, leo eget bibendum sodales, augue velit cursus nunc,"
                    ),
                    div(id="rightbox")(
                        "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis vitae, justo. Nullam dictum felis eu pede mollis pretium. Integer tincidunt. Cras dapibus. Vivamus elementum semper nisi. Aenean vulputate eleifend tellus. Aenean leo ligula, porttitor eu, consequat vitae, eleifend ac, enim. Aliquam lorem ante, dapibus in, viverra quis, feugiat a, tellus. Phasellus viverra nulla ut metus varius laoreet. Quisque rutrum. Aenean imperdiet. Etiam ultricies nisi vel augue. Curabitur ullamcorper ultricies nisi. Nam eget dui. Etiam rhoncus. Maecenas tempus, tellus eget condimentum rhoncus, sem quam semper libero, sit amet adipiscing sem neque sed ipsum. Nam quam nunc, blandit vel, luctus pulvinar, hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. Donec sodales sagittis magna. Sed consequat, leo eget bibendum sodales, augue velit cursus nunc,"
                    ),
                    div(id="footerdiv")(
                        "This is footerbox!"
                    )
                )
            )
        )
    )
    print str(src)
    #print str(style(type="text/css")(css))
    #print str(menu(entries, current=1, id="tabmenue"))
    
    