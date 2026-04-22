class Prompt:
    FILTER_LIST = """Catfishing is a game where players get the categories containing a secret wikipedia article, and need to guess which article is it.
        You are given the following list of Wikipedia article titles, and the list of categories each article is contained in. Pick 10 that would work well as secret articles for this game.
        Focus points:

        1. Don't pick articles that are impossible to guess from their categories. For instance, if the only categories are “Geography” and “Japan”, this is too broad to guess any specific Japanese-geography-related article.
        2. Don't pick articles that are too general/categorical. The article “Tetris” is good, the article “Video game” is not.
        3. The articles should be relatively well known for the average Israeli. At least 1% of Israeli people should have heard of each of the topics before, according to your estimate.

        Pick ten diverse articles, belonging to different areas of life. Don't pick two music-related articles, two food-related articles etc.

        Write the output in Hebrew this specific format, without any header or intro:

        <מספר>. <שם המאמר>

        ARTICLE_NAME should be the exact title of the article as given in the input list.

        The list of articles to select from:
        {input_list}
    """

    PICK_THEMES = """You are tasked with creating a daily, themed round for the Hebrew version the the game "Catfishing".
    In this game, players are given a list of categories and need to guess the secret Wikipedia article that belongs to those categories.
    First, I need you to pick the theme for today. The theme should be broad enough to allow for a variety of articles, but specific enough to make the game interesting.
    Propose 5 different interesting themes loosely inspired by today's date: {date}.
    For example, if the date is an Israeli holiday or close to one, some themes could be around that.
    If a famous event occured on that date in history, some themes could be around that.
    If a famous person was born or died on that date, some themes could be around that.

    Themes should be brief and not overly specific. For example, "Soccer World Cup" is a good theme, "the world cup 1998" is not.
    The theme should also be general enough to relate to articles of different kinds and areas of life.
    For example, if you pick the theme of 'Remarkable Israeli People', it would be hard to find related articles which are not about specific people.

    List the themes in Hebrew, and in this format exactly, without any header or intro:

    <מספר>. <רעיון לנושא>
    """

    # TODO: Add hard-coded list of areas of life and build a matrix of area-theme-article to make sure we pick diverse articles in the next step.

    PICK_ARTICLES = """You are tasked with creating a daily, themed round for the Hebrew version the the game "Catfishing".
    In this game, players are given a list of categories and need to guess the secret Wikipedia article that belongs to those categories.
    The theme for today's round is: {theme}.
    I need you to name people / places / things, which likely have a wikipedia page, and that are loosely related to this theme or inspired by it.
    Pick diverse articles, belonging to different areas of life. The articles should be specific enough to be gussable from their wikipedia categories.
    They should also range in difficulty, some should be more famous and easy to guess, and some should be harder.

    Start with 25 articles which are directly, thematically related to the theme.
    Then add 25 more articles which are loosely related to the theme by wordplay.
    Then add 50 more articles which are related to *something* that's associated with the theme, but not directly related to the theme itself. For example, if the theme is "passover", you can add articles related to "egypt" or "spring" or "freedom".

    For example, I made one themed for passover and I had the following article ideas:
    שרהל'ה שרון (because we sing in passover)
    החירות מובילה את העם (because passover is known as the holiday of freedom)
    מדבר אטקמה (because the story of passover takes place in the desert)
    אביב גפן (because passover is in the spring, and his name is literally "spring")
    אבן רוזטה (because it's related to ancient egypt like the story of passover)
    צ'יצ'ן איצה (because it's a pyramid, which are associated with egypt)
    רפלסיה גדולה (because it's the biggest flower, and passover is associated with the spring and blooming)
    משפט הסדר הטוב (because it has the word סדר which is the name of the ritual meal in passover)
    ביצת פברז'ה (because it's an egg, and eggs are part of the passover meal)
    איגנץ זמלווייס (because he's associated with handwashing, and handwashing is part of the passover ritual)
    סימן שאלה (because we ask questions during the passover meal)
    צליאק (because it's a disease related to gluten, and we eat gluten-free matzah during passover)
    משה בתיבה (because it's a famous dish named after moses)

    Write the proposed article names in Hebrew, in this specific format, without any header or intro:

    <מספר>. <שם המאמר>

    I remind you that the theme for today is {theme}.
    """

    FILTER_LIST_AND_CATEGORIES = """Catfishing is a game where players get the categories containing a secret wikipedia article, and need to guess which article is it.
    You are given the following list of Wikipedia article titles, and the list of categories each article is contained in. Pick 10 that would work well as secret articles for this game.
    Focus points:

    1. Some of the categories are too revealing. For example, the category “Tbilisi” for the article about the city of Tbilisi, or the category “Shirley Temple” for the article about the article “Shirley Temple (Cocktail)”. Remove those categories when considering articles.
    2. Don't pick articles that are impossible to guess from their categories (after filtering out the revealing categories mentioned above), For instance, if the only categories are “Geography” and “Japan”, this is too broad to guess any specific Japanese-geography-related article.
    3. Don't pick articles that are too general/categorical. The article “Tetris” is good, the article “Video game” is not.
    4. The articles should be relatively well known for the average Israeli. At least 1% of Israeli people should have heard of each of the topics before, according to your estimate.

    Pick ten diverse articles, no two should belong to a similar area of life. Don't pick two music-related articles, two food-related articles etc.
    For example, I made one themed for passover and I had the following article ideas:
    שרהל'ה שרון (because we sing in passover)
    מדבר אטקמה (because the story of passover takes place in the desert)
    אביב גפן (because passover is in the spring, and his name is literally "spring")
    אבן רוזטה (because it's related to ancient egypt like the story of passover)
    צ'יצ'ן איצה (because it's a pyramid, which are associated with egypt)
    רפלסיה גדולה (because it's the biggest flower, and passover is associated with the spring and blooming)
    משפט הסדר הטוב (because it has the word סדר which is the name of the ritual meal in passover)
    ביצת פברז'ה (because it's an egg, and eggs are part of the passover meal)
    איגנץ זמלווייס (because he's associated with handwashing, and handwashing is part of the passover ritual)
    סימן שאלה (because we ask questions during the passover meal)
    משה בתיבה (because it's a famous dish named after moses)
    
    Write the output in this specific format, without any header or intro:

    <NUMBER>. Article: <ARTICLE_NAME>. Categories: <FILTERED_CATEGORY_LIST>

    ARTICLE_NAME should be the exact title of the article as given in the input list.
    FILTERED_CATEGORY_LIST should contain the list of categories, comma separated, after removing the revealing categories mentioned above.

    The list of articles to select from:
    {input_list}
    """