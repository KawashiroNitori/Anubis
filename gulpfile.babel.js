/**
 * Created by Nitori on 2016/12/30.
 */
'use strict';
import gulp from 'gulp';
import svgmin from 'gulp-svgmin';
import iconfont from 'gulp-iconfont';
import nunjucks from 'gulp-nunjucks';
import generateConstant from './scripts/build/constant/gulp';
import generateLocale from './scripts/build/constant/gulp';

const iconTimestamp = ~~(Date.now() / 1000);

gulp.task('constant', () => {
    return gulp
        .src('anubis/ui/constant/*.js')
        .pipe(generateConstant())
        .pipe(gulp.dest('anubis/constant'))
});

gulp.task('iconfont', () => {
    return gulp
        .src('anubis/ui/misc/icons/*.svg')
        .pipe(svgmin())
        .pipe(gulp.dest('anubis/ui/misc/icons'))
        .pipe(iconfont({
            fontHeight: 1000,
            prependUnicode: false,
            descent: 6.25 / 100 * 1000,
            fontName: 'anubisIcon',
            formats: ['svg', 'ttf', 'eot', 'woff', 'woff2'],
            timestamp: iconTimestamp,
        }))
        .on('glyphs', (glyphs, options) => {
            gulp
                .src('anubis/ui/misc/icons/template/*.styl')
                .pipe(nunjucks.compile({glyphs, options}))
                .pipe(gulp.dest('anubis/ui/misc/.iconfont'))
        })
        .pipe(gulp.dest('anubis/ui/misc/.iconfont'));
});

gulp.task('locale', () => {
    return gulp
        .src('anubis/locale/*.yaml')
        .pipe(generateLocale())
        .pipe(gulp.dest('anubis/ui/static/locale'))
});

gulp.task('default', ['iconfont', 'constant', 'locale'], () => {});
