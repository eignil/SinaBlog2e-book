# -*- coding: utf-8 -*-
import copy

from src.container.initialbook import HtmlBookPackage
from src.container.image import ImageContainer
from src.lib.epub.epub import Epub
from src.tools.config import Config
from src.tools.html_creator import HtmlCreator
from src.tools.match import Match
from src.tools.path import Path
from src.tools.template_config import TemplateConfig
from src.tools.type import Type
from src.tools.debug import Debug


class Book(object):
    u"""
    负责将Book转换为Epub
    """

    def __init__(self, raw_sql_book_list):
        # Debug.logger.debug("raw_sql_book['SinaBlog'][0].sql.info:" + str(raw_sql_book_list['SinaBlog'][0].sql.info))
        raw_book_list = [book.catch_data() for book in self.flatten(raw_sql_book_list)]
        # raw_book_list是InitialBook对象的列表
        Debug.logger.debug(u"raw_book_list[0].kind是什么鬼?" + str(raw_book_list[0].kind))
        Debug.logger.debug(u"raw_book_list[0].epub.article_count是什么鬼?" + str(raw_book_list[0].epub.article_count))
        Debug.logger.debug(u"raw_book_list[0].epub.char_count是什么鬼?" + str(raw_book_list[0].epub.char_count))
        Debug.logger.debug(u"raw_book_list[0].epub.title是什么鬼?" + str(raw_book_list[0].epub.title))
        Debug.logger.debug(u"raw_book_list[0].epub.id是什么鬼?" + str(raw_book_list[0].epub.id))
        Debug.logger.debug(u"raw_book_list[0].epub.split_index是什么鬼?" + str(raw_book_list[0].epub.split_index))
        Debug.logger.debug(u"raw_book_list[0].epub.prefix:" + str(raw_book_list[0].epub.prefix))
        Debug.logger.debug(u"raw_book_list是什么????" + str(raw_book_list[0]))
        # Debug.logger.debug(u"raw_book_list[0].article_list" + str(raw_book_list[0].article_list))
        Debug.logger.debug(u"raw_book_list[0].page_list" + str(raw_book_list[0].page_list))
        # Debug.logger.debug(u"raw_book_list[0].article_list" + str(raw_book_list[0].article_list))

        book_list = self.volume_book(raw_book_list)
        # Debug.logger.debug("执行前book_list是什么??" + str(book_list))
        # print u"执行前, book_list为:" + str(book_list)
        self.book_list = [self.create_book_package(book) for book in book_list]
        # print (u"执行后, book_list为:" + str(book_list))
        return

    @staticmethod
    def flatten(task_list):
        book_list = []
        for kind in Type.type_list:
            if kind in task_list:
                book_list += task_list[kind]
        return book_list

    @staticmethod
    def volume_book(raw_book_list):
        def split(raw_book, surplus, index=1):
            if (raw_book.epub.answer_count <= surplus) or (raw_book.epub.article_count <= 1):
                raw_book.epub.split_index = index
                return [raw_book]
            article_list = []
            while surplus > 0:
                article = raw_book.article_list[0]
                raw_book.article_list = raw_book.article_list[1:]
                article_list.append(article)
                surplus -= article['answer_count']
                raw_book.epub.answer_count -= article['answer_count']    # 文章数量
            book = copy.deepcopy(raw_book)
            book.set_article_list(article_list)
            book.epub.split_index = index
            return [book] + split(raw_book, Config.max_answer, index + 1)

        counter = 0
        book = []
        book_list = []
        while len(raw_book_list):
            raw_book = raw_book_list.pop()
            if not raw_book.epub.answer_count:
                # 若书中没有文章则直接跳过
                continue
            if (counter + raw_book.epub.answer_count) < Config.max_answer:
                book.append(raw_book)
            elif (counter + raw_book.epub.answer_count) == Config.max_answer:
                book.append(raw_book)
                book_list.append(book)
                book = []
                counter = 0
            elif (counter + raw_book.epub.answer_count) > Config.max_answer:
                split_list = split(raw_book, Config.max_answer - counter)
                book.append(split_list[0])
                book_list.append(book)
                book = []
                counter = 0
                raw_book_list = split_list[1:] + raw_book_list
        book_list.append(book)
        return book_list

    def book_to_html(self, book, index, creator):
        if book.epub.split_index:
            book.epub.title += "_({})".format(book.epub.split_index)

        book.epub.prefix = index

        page = creator.create_info_page(book)
        book.page_list.append(page)
        # print u'article_list???' + str(book.article_list)
        for article in book.article_list:
            if book.kind in Type.SinaBlog:          # 目前只有SinaBlog这一种情况
                page = creator.create_article(article, index)
            else:       # 下面的代码暂时是不会执行的
                page = creator.create_SinaBlog_single(article, index)
            book.page_list.append(page)
        return book

    def create_book_package(self, book_list):
        u"""

        :param book_list:
        :return: HtmlBookPackage()
        """
        index = 0
        epub_book_list = []
        image_container = ImageContainer()
        creator = HtmlCreator(image_container)
        for book in book_list:
            epub_book = self.book_to_html(book, index, creator)
            epub_book_list.append(epub_book)
            index += 1

        book_package = HtmlBookPackage()
        book_package.book_list = epub_book_list
        book_package.image_list = image_container.get_filename_list()
        book_package.image_container = image_container
        return book_package

    def create_book(self, book_package):
        book_package.image_container.set_save_path(Path.image_pool_path)
        book_package.image_container.start_download()
        title = book_package.get_title()
        Debug.logger.debug(u"电子书的名称是???" + str(title))
        if not title:
            # 电子书题目为空时自动跳过
            # 否则会发生『rm -rf / 』的惨剧
            return
        Path.chdir(Path.base_path + u'/电子书临时资源库')
        epub = Epub(title)
        html_tmp_path = Path.html_pool_path + u'/'
        image_tmp_path = Path.image_pool_path + u'/'
        epub.set_creator(u'SinaBlogV01')
        epub.set_book_id()
        epub.set_output_path(Path.result_path)
        epub.add_css(Path.base_path + u'/www/css/markdown.css')
        epub.add_css(Path.base_path + u'/www/css/customer.css')
        epub.add_css(Path.base_path + u'/www/css/normalize.css')
        epub.add_css(Path.base_path + u'/www/css/bootstrap.css')
        # epub.add_css(Path.base_path + u'/www/css/article.css')    # TODO: 来自新浪,需要精简
        for book in book_package.book_list:
            page = book.page_list[0]
            with open(html_tmp_path + page.filename, u'w') as html:
                html.write(page.content)
            if '_' in page.title:
                page.title = ''.join(page.title.split('_')[1:])  # 删除章节前缀
            epub.create_chapter(html_tmp_path + page.filename, page.title)
            for page in book.page_list[1:]:
                with open(html_tmp_path + page.filename, u'w') as html:
                    html.write(page.content)
                epub.add_html(html_tmp_path + page.filename, page.title)
            epub.finish_chapter()
        for image in book_package.image_list:
            epub.add_image(image_tmp_path + image['filename'])
        epub.create()
        Path.reset_path()
        return

    def create_single_html_book(self, book_package):
        title = book_package.get_title()
        if not title:
            # 电子书题目为空时自动跳过
            # 否则会发生『rm -rf / 』的惨剧
            return
        Path.reset_path()
        Path.chdir(Path.result_path)
        Path.rmdir(u'./' + title)
        Path.mkdir(u'./' + title)
        Path.chdir(u'./' + title)
        page = []
        for book in book_package.book_list:
            page += book.page_list
        content = u' \r\n '.join([Match.html_body(x.content) for x in page]).replace(u'../images/', u'./images/')
        with open(TemplateConfig.content_base_uri) as html:
            content = html.read().format(title=title, body=content).replace(u'../style/', u'./')
        with open(title + u'.html', 'w') as html:
            html.write(content)
        Path.copy(Path.html_pool_path + u'/../{}/OEBPS/images'.format(title), u'./images')
        Path.copy(Path.www_css + u'/customer.css', u'./customer.css')
        Path.copy(Path.www_css + u'/markdown.css', u'./markdown.css')
        Path.copy(Path.www_css + u'/normalize.css', u'./normalize.css')
        # Path.copy(Path.www_css + u'/article.css', u'./article.css')         # TODO: 需要精简
        Path.reset_path()

        return

    def create(self):
        for book_package in self.book_list:
            self.create_book(book_package)
            self.create_single_html_book(book_package)
        return
